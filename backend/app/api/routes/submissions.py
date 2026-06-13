from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import (
    SubmissionsUnfrozen,
    VerifiedGuestOrHigher,
    VerifiedUserOrHigher,
    WorkerOrVerifiedUser,
    get_submission_service,
)
from app.api.services.submission import SubmissionService, SubmissionServiceError
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.game import GameType
from app.models.user import UserRole
from app.schemas.submission import SubmissionRead


router = APIRouter()


# POST /api/v1/submissions/
@router.post("", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(lambda: settings.RATE_LIMIT_UPLOAD)
async def create_submission(
    request: Request,  # noqa: ARG001
    file: Annotated[UploadFile, File(...)],
    game_type: Annotated[GameType, Form(...)],
    current_user: VerifiedUserOrHigher,
    _unfrozen: SubmissionsUnfrozen,
    service: SubmissionService = Depends(get_submission_service),
    name: Annotated[str | None, Form()] = None,
) -> SubmissionRead:
    """
    Upload an agent zip file and queue it for building. Requires the USER role
    or higher.
    """
    try:
        submission = await service.create_submission(current_user.id, file, game_type=game_type, name=name)
        return SubmissionRead.model_validate(submission)
    except SubmissionServiceError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# GET /api/v1/submissions/{submission_id}
@router.get("/{submission_id}", response_model=SubmissionRead)
def get_submission(
    submission_id: str,  # UUID
    actor: WorkerOrVerifiedUser,
    service: SubmissionService = Depends(get_submission_service),
) -> SubmissionRead:
    """
    Get a submission by ID. Accessible to the owning user, admins, and the
    worker (via x-api-key; needed by the build worker).
    """
    submission = service.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if (
        not actor.is_worker
        and submission.user_id != actor.user.id
        and actor.user.role != UserRole.ADMIN
    ):
        raise HTTPException(status_code=403, detail="Not authorized to view this submission")

    return SubmissionRead.model_validate(submission)


# GET /api/v1/submissions/{submission_id}/download
@router.get("/{submission_id}/download")
def download_submission(
    submission_id: str,  # UUID
    actor: WorkerOrVerifiedUser,
    service: SubmissionService = Depends(get_submission_service),
) -> FileResponse:
    """
    Download the zip file for a submission. Accessible to the owning user,
    admins, and the worker (via x-api-key; needed by the build worker).
    """
    submission = service.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if (
        not actor.is_worker
        and submission.user_id != actor.user.id
        and actor.user.role != UserRole.ADMIN
    ):
        raise HTTPException(status_code=403, detail="Not authorized to download this submission")

    try:
        file_path = service.get_submission_file_path(submission)
    except SubmissionServiceError as e:
        raise HTTPException(status_code=404, detail="Submission file not found") from e
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Submission file not found on disk")

    return FileResponse(
        path=file_path,
        media_type="application/zip",
        filename=f"{submission.id}.zip",
    )


# GET /api/v1/submissions/
@router.get("", response_model=list[SubmissionRead])
def list_submissions(
    current_user: VerifiedGuestOrHigher,
    service: SubmissionService = Depends(get_submission_service),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[SubmissionRead]:
    """
    List submissions for the current user. Requires a verified login.
    """
    submissions = service.list_user_submissions(current_user.id, skip, limit)
    return [SubmissionRead.model_validate(s) for s in submissions]


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(lambda: settings.RATE_LIMIT_MUTATIONS)
def delete_submission(
    request: Request,  # noqa: ARG001
    submission_id: UUID,
    current_user: VerifiedUserOrHigher,
    _unfrozen: SubmissionsUnfrozen,
    service: SubmissionService = Depends(get_submission_service),
) -> None:
    """Delete a submission. Requires the USER role or higher; owner or admin only."""
    try:
        service.delete_submission(submission_id, current_user.id, is_admin=current_user.role == UserRole.ADMIN)
    except SubmissionServiceError as e:
        detail = str(e)
        if detail == "Submission not found":
            raise HTTPException(status_code=404, detail=detail) from e
        if detail == "Not authorized to delete this submission":
            raise HTTPException(status_code=403, detail=detail) from e
        raise HTTPException(status_code=400, detail=detail) from e

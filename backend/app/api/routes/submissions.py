from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user, get_submission_service
from app.api.services.submission import SubmissionService
from app.models.user import User
from app.schemas.submission import SubmissionRead


router = APIRouter()


# POST /api/v1/submissions/
@router.post("/", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
async def create_submission(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    service: SubmissionService = Depends(get_submission_service),
) -> SubmissionRead:
    """
    Upload an agent zip file and queue it for building.
    """
    return await service.create_submission(current_user.id, file)


# GET /api/v1/submissions/{submission_id}
@router.get("/{submission_id}", response_model=SubmissionRead)
def get_submission(
    submission_id: str,  # UUID
    current_user: Annotated[User, Depends(get_current_user)],
    service: SubmissionService = Depends(get_submission_service),
) -> SubmissionRead:
    """
    Get a submission by ID.
    """
    submission = service.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Ideally check if user owns submission or is admin
    if submission.user_id != current_user.id and current_user.role != "admin":  # assuming role logic
        raise HTTPException(status_code=403, detail="Not authorized to view this submission")

    return submission


# GET /api/v1/submissions/
@router.get("/", response_model=list[SubmissionRead])
def list_submissions(
    current_user: Annotated[User, Depends(get_current_user)],
    service: SubmissionService = Depends(get_submission_service),
    skip: int = 0,
    limit: int = 20,
) -> list[SubmissionRead]:
    """
    List submissions for the current user.
    """
    return service.list_user_submissions(current_user.id, skip, limit)

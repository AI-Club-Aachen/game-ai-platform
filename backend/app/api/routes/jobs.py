from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import WorkerOrVerifiedUser, require_worker_api_key
from app.api.deps.services import (
    get_job_repository,
    get_job_service,
    get_match_service,
    get_submission_service,
)
from app.api.repositories.job import JobRepository
from app.api.services.job import JobService, JobServiceError
from app.api.services.match import MatchService
from app.api.services.submission import SubmissionService
from app.models.user import UserRole
from app.schemas.job import (
    BuildJobCreate,
    BuildJobRead,
    BuildJobUpdate,
    MatchJobRead,
    MatchJobUpdate,
)


router = APIRouter()


@router.get("/build/{job_id}", response_model=BuildJobRead)
def get_build_job(
    job_id: UUID,
    actor: WorkerOrVerifiedUser,
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    submission_service: Annotated[SubmissionService, Depends(get_submission_service)],
) -> BuildJobRead:
    """Get a build job by ID. Worker API key, the submission owner, or an admin."""
    job = job_repository.get_build_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Build job not found",
        )
    if not actor.is_worker and actor.user.role != UserRole.ADMIN:
        submission = submission_service.get_submission(str(job.submission_id))
        if not submission or submission.user_id != actor.user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this build job",
            )
    return job


@router.patch("/build/{job_id}", response_model=BuildJobRead, dependencies=[Depends(require_worker_api_key)])
def update_build_job(
    job_id: UUID,
    update: BuildJobUpdate,
    submission_service: Annotated[SubmissionService, Depends(get_submission_service)],
) -> BuildJobRead:
    """Update a build job. Worker API key required."""
    job = submission_service.update_build_job(
        str(job_id),
        update.status,
        update.logs,
        update.image_id,
        update.image_tag,
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Build job not found",
        )
    return job


@router.post(
    "",
    response_model=BuildJobRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_worker_api_key)],
)
def create_build_job(
    build_job_create: BuildJobCreate,
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> BuildJobRead:
    """Create a new build job outside the normal submission flow. Worker API key required."""
    try:
        return job_service.create_build_job_for_submission(build_job_create)
    except JobServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/match/{job_id}", response_model=MatchJobRead)
def get_match_job(
    job_id: UUID,
    _actor: WorkerOrVerifiedUser,
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
) -> MatchJobRead:
    """Get a match job by ID. Worker API key or any verified login (status only)."""
    job = job_repository.get_match_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match job not found",
        )
    return job


@router.patch("/match/{job_id}", response_model=MatchJobRead, dependencies=[Depends(require_worker_api_key)])
async def update_match_job(
    job_id: UUID,
    update: MatchJobUpdate,
    match_service: Annotated[MatchService, Depends(get_match_service)],
) -> MatchJobRead:
    """Update a match job. Worker API key required."""
    job = await match_service.update_match_job(
        str(job_id),
        update.status,
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match job not found",
        )
    return job

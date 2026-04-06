from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps.services import (
    get_job_repository,
    get_match_service,
    get_submission_service,
)
from app.api.repositories.job import JobRepository
from app.api.services.match import MatchService
from app.api.services.submission import SubmissionService
from app.schemas.job import (
    BuildJobRead,
    BuildJobUpdate,
    MatchJobRead,
    MatchJobUpdate,
)


router = APIRouter()


@router.get("/build/{job_id}", response_model=BuildJobRead)
def get_build_job(
    job_id: UUID,
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
) -> BuildJobRead:
    """Get a build job by ID."""
    job = job_repository.get_build_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Build job not found",
        )
    return job


@router.patch("/build/{job_id}", response_model=BuildJobRead)
def update_build_job(
    job_id: UUID,
    update: BuildJobUpdate,
    submission_service: Annotated[SubmissionService, Depends(get_submission_service)],
) -> BuildJobRead:
    """Update a build job (used by workers)."""
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


@router.get("/match/{job_id}", response_model=MatchJobRead)
def get_match_job(
    job_id: UUID,
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
) -> MatchJobRead:
    """Get a match job by ID."""
    job = job_repository.get_match_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match job not found",
        )
    return job


@router.patch("/match/{job_id}", response_model=MatchJobRead)
async def update_match_job(
    job_id: UUID,
    update: MatchJobUpdate,
    match_service: Annotated[MatchService, Depends(get_match_service)],
) -> MatchJobRead:
    """Update a match job (used by workers)."""
    job = await match_service.update_match_job(
        str(job_id),
        update.status,
        update.logs,
        update.result,
        update.game_state,
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match job not found",
        )
    return job

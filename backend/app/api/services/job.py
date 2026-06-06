import logging

from app.api.repositories.agent import AgentRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.submission import SubmissionRepository
from app.models.job import BuildJob
from app.schemas.job import BuildJobCreate


logger = logging.getLogger(__name__)


class JobServiceError(Exception):
    """Base exception for match and build job service errors."""


class JobService:
    """Service for managing match and build jobs."""

    def __init__(
        self,
        job_repository: JobRepository,
        agent_repository: AgentRepository,
        submission_repository: SubmissionRepository,
    ) -> None:
        self._job_repository = job_repository
        self._agent_repository = agent_repository
        self._submission_repository = submission_repository

    def create_build_job_for_submission(self, build_job_create: BuildJobCreate) -> BuildJob:
        """Create a build job for a submission."""
        # Validate submission and agent
        submission = self._submission_repository.get_by_id(build_job_create.submission_id)
        if not submission:
            raise JobServiceError(f"Submission {build_job_create.submission_id} not found for build job creation.")
        # Create build job
        job = BuildJob(
            submission_id=build_job_create.submission_id,
            status=build_job_create.status,
            cleanup_image=build_job_create.cleanup_image,
        )

        return self._job_repository.save_build_job(job)

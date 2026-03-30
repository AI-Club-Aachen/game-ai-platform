import shutil
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from app.api.repositories.agent import AgentRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.submission import SubmissionRepository, SubmissionRepositoryError
from app.core.config import settings
from app.core.queue import job_queue
from app.models.job import BuildJob, JobStatus
from app.models.submission import Submission


class SubmissionServiceError(Exception):
    """Base exception for submission service errors."""


class SubmissionService:
    """Service for managing submissions."""

    def __init__(
        self,
        submission_repository: SubmissionRepository,
        job_repository: JobRepository,
        agent_repository: AgentRepository,
    ) -> None:
        self._repository = submission_repository
        self._job_repository = job_repository
        self._agent_repository = agent_repository
        # Directory to store uploaded zips temporarily or permanently
        self._upload_dir = Path(settings.SUBMISSIONS_DIR)

    async def create_submission(
        self,
        user_id: UUID,
        file: UploadFile,
    ) -> Submission:
        """
        Handle the full submission process:
        1. Create DB record (queued)
        2. Save file to disk
        3. Enqueue build job
        """
        if not file.filename or not file.filename.endswith(".zip"):
            raise SubmissionServiceError("Only .zip files are allowed.")

        # 1. Create initial record
        submission = Submission(user_id=user_id, object_path="pending")
        submission = self._repository.save(submission)

        # 2. Save file
        safe_filename = f"{submission.id}.zip"
        file_path = self._upload_dir / safe_filename

        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            self._repository.delete(submission)
            raise SubmissionServiceError(f"Failed to save file: {e}") from e

        # Update path
        submission.object_path = str(file_path.absolute())
        self._repository.save(submission)

        # 3. Create job record
        job = BuildJob(submission_id=submission.id, status=JobStatus.QUEUED)
        job = self._job_repository.save_build_job(job)

        # 4. Enqueue job
        await job_queue.enqueue_build(submission.id, submission.object_path, job.id)

        return submission

    def get_submission(self, submission_id: str | UUID) -> Submission | None:
        return self._repository.get_by_id(submission_id)

    def update_build_job(
        self,
        job_id: str,
        status: str,
        logs: str | None = None,
        image_id: str | None = None,
        image_tag: str | None = None,
    ) -> BuildJob | None:
        """Update build job and sync status to submission."""
        job = self._job_repository.get_build_job(job_id)
        if not job:
            return None

        job.status = status
        if logs is not None:
            job.logs += logs + "\n"
        if image_id is not None:
            job.image_id = image_id
        if image_tag is not None:
            job.image_tag = image_tag

        return self._job_repository.save_build_job(job)

    def delete_submission(self, submission_id: UUID, current_user_id: UUID, is_admin: bool = False) -> None:
        submission = self.get_submission(submission_id)
        if not submission:
            raise SubmissionServiceError("Submission not found")

        if not is_admin and submission.user_id != current_user_id:
            raise SubmissionServiceError("Not authorized to delete this submission")

        linked_agents = self._agent_repository.list_by_active_submission_id(submission.id)
        for agent in linked_agents:
            agent.active_submission_id = None
            self._agent_repository.save(agent)

        try:
            self._repository.delete(submission)
        except SubmissionRepositoryError as e:
            raise SubmissionServiceError("Failed to delete submission") from e

        file_path = Path(submission.object_path)
        if file_path.exists():
            file_path.unlink()

    def list_user_submissions(
        self,
        user_id: UUID,
        skip: int,
        limit: int,
    ) -> list[Submission]:
        return self._repository.list_by_user(user_id, skip, limit)

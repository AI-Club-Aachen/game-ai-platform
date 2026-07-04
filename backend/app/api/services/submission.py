from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from app.api.repositories.agent import AgentRepository
from app.api.repositories.arena import ArenaRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.submission import SubmissionRepository, SubmissionRepositoryError
from app.core.config import settings
from app.core.payload_limits import cap_log_append
from app.core.queue import job_queue
from app.models.game import GameType
from app.models.job import BuildJob, JobStatus
from app.models.submission import Submission


# Accepted ZIP upload content types. A missing/empty header is tolerated
# (see _validate_upload) since some clients omit it.
_ALLOWED_UPLOAD_CONTENT_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",
    "multipart/x-zip",
}

_UPLOAD_CHUNK_SIZE = 1024 * 1024


class SubmissionServiceError(Exception):
    """Base exception for submission service errors."""


class SubmissionService:
    """Service for managing submissions."""

    def __init__(
        self,
        submission_repository: SubmissionRepository,
        job_repository: JobRepository,
        agent_repository: AgentRepository,
        arena_repository: ArenaRepository,
    ) -> None:
        self._repository = submission_repository
        self._job_repository = job_repository
        self._agent_repository = agent_repository
        self._arena_repository = arena_repository
        # Directory to store uploaded zips temporarily or permanently
        self._upload_dir = Path(settings.SUBMISSIONS_DIR)

    async def create_submission(
        self,
        user_id: UUID,
        file: UploadFile,
        arena_id: UUID,
        name: str | None = None,
        cleanup_image: bool = True,
    ) -> Submission:
        """
        Handle the full submission process:
        1. Create DB record (queued)
        2. Save file to disk
        3. Enqueue build job
        """
        self._validate_upload(user_id, file)

        # Fetch arena to validate and get game_type
        arena = self._arena_repository.get_by_id(arena_id)
        if not arena or not arena.is_active:
            raise SubmissionServiceError("Target arena not found or inactive")
        game_type = arena.game_type

        # 1. Create initial record
        submission = Submission(user_id=user_id, name=name or "", game_type=game_type, arena_id=arena_id, object_path="pending")
        if not submission.name.strip():
            submission.name = str(submission.id)
        submission = self._repository.save(submission)

        # 2. Save file. Store only the relative key, never an absolute path (M-2).
        safe_filename = f"{submission.id}.zip"
        file_path = self._upload_dir / safe_filename
        self._upload_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._write_capped(file, file_path)
        except SubmissionServiceError:
            file_path.unlink(missing_ok=True)
            self._repository.delete(submission)
            raise
        except Exception as e:
            file_path.unlink(missing_ok=True)
            self._repository.delete(submission)
            raise SubmissionServiceError(f"Failed to save file: {e}") from e

        # Update path with the relative key only.
        submission.object_path = safe_filename
        self._repository.save(submission)

        # 3. Create job record
        job = BuildJob(submission_id=submission.id, status=JobStatus.QUEUED, cleanup_image=cleanup_image)
        job = self._job_repository.save_build_job(job)

        # 4. Enqueue job
        await job_queue.enqueue_build(submission.id, job.id, job.cleanup_image)

        return submission

    def _validate_upload(self, user_id: UUID, file: UploadFile) -> None:
        """Pre-save upload validation: content type, advertised size, and quota (H-4)."""
        if file.content_type and file.content_type not in _ALLOWED_UPLOAD_CONTENT_TYPES:
            raise SubmissionServiceError(f"Unsupported content type: {file.content_type}")

        max_bytes = settings.MAX_UPLOAD_BYTES
        if max_bytes and file.size is not None and file.size > max_bytes:
            raise SubmissionServiceError(f"Upload exceeds the maximum allowed size of {max_bytes} bytes.")

        quota = settings.MAX_SUBMISSIONS_PER_USER
        if quota:
            existing = self._repository.list_by_user(user_id, skip=0, limit=quota + 1)
            if len(existing) >= quota:
                raise SubmissionServiceError(f"Submission quota of {quota} reached.")

    def _write_capped(self, file: UploadFile, file_path: Path) -> None:
        """Stream the upload to disk, enforcing MAX_UPLOAD_BYTES even if the
        advertised Content-Length was missing or wrong (H-4)."""
        max_bytes = settings.MAX_UPLOAD_BYTES
        written = 0
        with file_path.open("wb") as buffer:
            while chunk := file.file.read(_UPLOAD_CHUNK_SIZE):
                written += len(chunk)
                if max_bytes and written > max_bytes:
                    raise SubmissionServiceError(
                        f"Upload exceeds the maximum allowed size of {max_bytes} bytes."
                    )
                buffer.write(chunk)

    def get_submission(self, submission_id: str | UUID) -> Submission | None:
        return self._repository.get_by_id(submission_id)

    def _resolve_submission_file(self, object_path: str) -> Path:
        """Resolve a stored object_path to a real file under SUBMISSIONS_DIR (M-2).

        Only the basename is trusted, which neutralizes legacy rows that stored an
        absolute path as well as any path-traversal value. The result is verified
        to stay within the submissions directory and must not be a symlink.
        """
        base = self._upload_dir.resolve()
        # Extract basename only.
        key = Path(object_path).name
        if not key:
            raise SubmissionServiceError("Invalid submission path")

        candidate = base / key
        if candidate.is_symlink():
            raise SubmissionServiceError("Refusing to access a submission stored as a symlink")

        resolved = candidate.resolve()
        try:
            resolved.relative_to(base)
        except ValueError as e:
            raise SubmissionServiceError("Submission path escapes the submissions directory") from e
        return resolved

    def get_submission_file_path(self, submission: Submission) -> Path:
        """Return the on-disk path for a submission's ZIP, validated for containment."""
        return self._resolve_submission_file(submission.object_path)

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

        job.status = JobStatus(status)
        if logs is not None:
            # Truncate server-side.
            job.logs = cap_log_append(
                job.logs,
                logs,
                append_cap=settings.MAX_LOG_APPEND_BYTES,
                total_cap=settings.MAX_TOTAL_LOG_BYTES,
            )
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

        # Resolve before unlinking to ensure containment.
        try:
            file_path = self._resolve_submission_file(submission.object_path)
        except SubmissionServiceError:
            return
        if file_path.exists():
            file_path.unlink()

    def list_user_submissions(
        self,
        user_id: UUID,
        skip: int,
        limit: int,
    ) -> list[Submission]:
        return self._repository.list_by_user(user_id, skip, limit)

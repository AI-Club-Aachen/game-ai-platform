import logging
from uuid import UUID

from sqlmodel import Session, select

from app.models.submission import Submission


logger = logging.getLogger(__name__)


class SubmissionRepositoryError(Exception):
    """Base exception for submission repository errors."""


class SubmissionRepository:
    """Repository for Submission aggregate."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Queries ---

    def get_by_id(self, submission_id: str) -> Submission | None:
        return self._session.get(Submission, submission_id)

    def list_by_user(
        self,
        user_id: UUID,
        skip: int,
        limit: int,
    ) -> list[Submission]:
        """List submissions for a specific user."""
        statement = (
            select(Submission)
            .where(Submission.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Submission.created_at.desc())
        )
        return list(self._session.exec(statement).all())

    # --- Commands ---

    def save(self, submission: Submission) -> Submission:
        """Persist submission, handling commit/rollback."""
        try:
            self._session.add(submission)
            self._session.commit()
            self._session.refresh(submission)
        except Exception as e:
            self._session.rollback()
            logger.exception("Error saving submission %s", getattr(submission, "id", None))
            raise SubmissionRepositoryError("Failed to persist submission") from e
        else:
            return submission

    def delete(self, submission: Submission) -> None:
        """Delete submission, handling commit/rollback."""
        try:
            self._session.delete(submission)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            logger.exception("Error deleting submission %s", getattr(submission, "id", None))
            raise SubmissionRepositoryError("Failed to delete submission") from e

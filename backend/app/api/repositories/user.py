import logging
from uuid import UUID

from sqlalchemy import case
from sqlmodel import Session, func, select

from app.models.agent import Agent
from app.models.agent_container import AgentContainer
from app.models.submission import Submission
from app.models.user import User, UserRole


logger = logging.getLogger(__name__)


class UserRepositoryError(Exception):
    """Base exception for user repository errors."""


class UserRepository:
    """Repository for User aggregate."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Queries ---

    def get_by_id(self, user_id: UUID) -> User | None:
        statement = select(User).where(User.id == user_id)
        return self._session.exec(statement).first()

    def get_by_username_ci(self, username: str) -> User | None:
        """Case-insensitive username lookup."""
        statement = select(User).where(
            User.username.ilike(username)  # type: ignore[attr-defined]
        )
        return self._session.exec(statement).first()

    def get_by_email_ci(self, email: str) -> User | None:
        """Case-insensitive email lookup."""
        statement = select(User).where(
            User.email.ilike(email)  # type: ignore[attr-defined]
        )
        return self._session.exec(statement).first()

    def list_users(
        self,
        skip: int,
        limit: int,
        role: UserRole | None = None,
        email_verified: bool | None = None,
    ) -> tuple[list[User], int]:
        """List users with optional filters and pagination."""
        statement = select(User)
        count_statement = select(func.count()).select_from(User)

        if role is not None:
            statement = statement.where(User.role == role)
            count_statement = count_statement.where(User.role == role)

        if email_verified is not None:
            statement = statement.where(User.email_verified == email_verified)
            count_statement = count_statement.where(User.email_verified == email_verified)

        total: int = self._session.exec(count_statement).one()
        statement = (
            statement.offset(skip)
            .limit(limit)
            .order_by(
                User.created_at.desc()  # type: ignore[attr-defined]
            )
        )
        users: list[User] = list(self._session.exec(statement).all())

        return users, total

    def get_admin_user_stats(self, user_ids: list[UUID]) -> dict[UUID, dict[str, object]]:
        """Aggregate compact admin stats for the provided users."""
        stats: dict[UUID, dict[str, object]] = {
            user_id: {
                "agents_count": 0,
                "submissions_count": 0,
                "matches_played_total": 0,
                "running_containers_count": 0,
                "failed_containers_count": 0,
                "latest_submission_at": None,
            }
            for user_id in user_ids
        }

        if not user_ids:
            return stats

        agent_statement = (
            select(
                Agent.user_id,
                func.count(Agent.id),
                func.coalesce(func.sum(Agent.matches_played), 0),
            )
            .where(Agent.user_id.in_(user_ids))  # type: ignore[attr-defined]
            .group_by(Agent.user_id)
        )
        for user_id, agents_count, matches_played_total in self._session.exec(agent_statement).all():
            stats[user_id]["agents_count"] = int(agents_count or 0)
            stats[user_id]["matches_played_total"] = int(matches_played_total or 0)

        submission_statement = (
            select(
                Submission.user_id,
                func.count(Submission.id),
                func.max(Submission.created_at),
            )
            .where(Submission.user_id.in_(user_ids))  # type: ignore[attr-defined]
            .group_by(Submission.user_id)
        )
        for user_id, submissions_count, latest_submission_at in self._session.exec(submission_statement).all():
            stats[user_id]["submissions_count"] = int(submissions_count or 0)
            stats[user_id]["latest_submission_at"] = latest_submission_at

        normalized_status = func.lower(AgentContainer.status)
        container_statement = (
            select(
                Agent.user_id,
                func.coalesce(func.sum(case((normalized_status == "running", 1), else_=0)), 0),
                func.coalesce(
                    func.sum(
                        case(
                            (normalized_status.in_(["failed", "unhealthy", "exited", "dead"]), 1),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .join(Agent, AgentContainer.agent_id == Agent.id)
            .where(Agent.user_id.in_(user_ids))  # type: ignore[attr-defined]
            .group_by(Agent.user_id)
        )
        for user_id, running_count, failed_count in self._session.exec(container_statement).all():
            stats[user_id]["running_containers_count"] = int(running_count or 0)
            stats[user_id]["failed_containers_count"] = int(failed_count or 0)

        return stats

    def get_unverified_with_verification_tokens(self) -> list[User]:
        """
        Users that are not verified and have a verification token set.
        Used by email verification flows.
        """
        statement = select(User).where(
            User.email_verified == False,  # noqa: E712
            User.email_verification_token_hash != None,  # noqa: E711
        )
        return list(self._session.exec(statement).all())

    def get_with_active_reset_tokens(self) -> list[User]:
        """
        Users that have a password reset token set.
        Used by password reset flows.
        """
        statement = select(User).where(
            User.password_reset_token_hash != None  # noqa: E711
        )
        return list(self._session.exec(statement).all())

    # --- Commands (transactions live here) ---

    def save(self, user: User) -> User:
        """Persist user, handling commit/rollback."""
        try:
            self._session.add(user)
            self._session.commit()
            self._session.refresh(user)
        except Exception as e:
            self._session.rollback()
            logger.exception("Error saving user %s", getattr(user, "id", None))
            raise UserRepositoryError("Failed to persist user") from e
        else:
            return user

    def delete(self, user: User) -> None:
        """Delete user, handling commit/rollback."""
        try:
            self._session.delete(user)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            logger.exception("Error deleting user %s", getattr(user, "id", None))
            raise UserRepositoryError("Failed to delete user") from e

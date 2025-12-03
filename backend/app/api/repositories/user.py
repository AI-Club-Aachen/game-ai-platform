import logging
from uuid import UUID

from sqlmodel import Session, func, select

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

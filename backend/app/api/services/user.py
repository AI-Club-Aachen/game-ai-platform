import logging
from datetime import UTC, datetime
from uuid import UUID

from app.api.repositories.user import UserRepository, UserRepositoryError
from app.core.security import hash_password, validate_password_strength, verify_password
from app.models.user import User, UserRole
from app.schemas.user import PasswordChangeRequest, UserRoleUpdate, UserUpdate


logger = logging.getLogger(__name__)


# --- Domain / application exceptions (non-HTTP) ---


class UserServiceError(Exception):
    """Base exception for user service errors."""


class UserNotFoundError(UserServiceError):
    """Raised when a user cannot be found."""


class UserConflictError(UserServiceError):
    """Raised when a uniqueness or similar conflict occurs (username/email)."""


class UserPermissionError(UserServiceError):
    """Raised when the current user is not allowed to perform an action."""


class UserValidationError(UserServiceError):
    """Raised when provided data is invalid (e.g. password rules)."""


class UserService:
    """Application service for user-related operations."""

    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    # --- Current user profile ---

    def update_current_user_profile(
        self,
        current_user: User,
        user_update: UserUpdate,
    ) -> User:
        """Update username/email for current user, enforcing uniqueness rules."""
        # Username update
        if user_update.username is not None:
            username_lower = user_update.username.lower()
            if username_lower != current_user.username.lower():
                existing_user = self._repo.get_by_username_ci(username_lower)
                if existing_user and existing_user.id != current_user.id:
                    logger.warning("Username update conflict: %s already taken", user_update.username)
                    raise UserConflictError("Username already taken")

            current_user.username = user_update.username
            logger.info("Username updated for user %s", current_user.id)

        # Email update
        if user_update.email is not None:
            email_lower = str(user_update.email).lower()
            if email_lower != current_user.email.lower():
                existing_user = self._repo.get_by_email_ci(email_lower)
                if existing_user and existing_user.id != current_user.id:
                    logger.warning("Email update conflict: %s already in use", user_update.email)
                    raise UserConflictError("Email already in use")

            current_user.email = str(user_update.email)
            current_user.email_verified = False
            logger.info("Email updated for user %s - re-verification required", current_user.id)

        if user_update.username is None and user_update.email is None:
            # Nothing to change
            return current_user

        current_user.updated_at = datetime.now(UTC)

        try:
            return self._repo.save(current_user)
        except UserRepositoryError as e:
            logger.exception("Error updating user profile for %s", current_user.id)
            raise UserServiceError("Failed to update profile") from e

    # --- Password change for current user ---

    def change_password(
        self,
        current_user: User,
        password_request: PasswordChangeRequest,
    ) -> None:
        """
        Change the current user's password, enforcing current-password check and strength rules.
        """
        if not verify_password(password_request.current_password, current_user.password_hash):
            logger.warning("Failed password change attempt for user %s", current_user.id)
            raise UserValidationError("Current password is incorrect")

        try:
            validate_password_strength(password_request.new_password)
        except ValueError as e:
            logger.warning("Weak password provided during change for user %s", current_user.id)
            raise UserValidationError(str(e)) from e

        if verify_password(password_request.new_password, current_user.password_hash):
            raise UserValidationError("New password must be different from current password")

        try:
            current_user.password_hash = hash_password(password_request.new_password)
            current_user.updated_at = datetime.now(UTC)
            self._repo.save(current_user)
            logger.info("Password changed successfully for user %s", current_user.id)
        except UserRepositoryError as e:
            logger.exception("Error changing password for %s", current_user.id)
            raise UserServiceError("Failed to change password") from e

    # --- Admin operations: list, get, role update, delete, verification email ---

    def list_users(
        self,
        skip: int,
        limit: int,
        role: UserRole | None = None,
        email_verified: bool | None = None,
    ) -> tuple[list[User], int]:
        """Admin: list users with filters and pagination."""
        try:
            return self._repo.list_users(skip=skip, limit=limit, role=role, email_verified=email_verified)
        except UserRepositoryError as e:
            logger.exception("Error listing users")
            raise UserServiceError("Failed to list users") from e

    def get_user_by_id(self, user_id: UUID) -> User:
        """Admin: get user by id or raise."""
        user = self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError("User not found")
        return user

    def update_user_role(
        self,
        admin: User,
        user_id: UUID,
        role_update: UserRoleUpdate,
    ) -> User:
        """Admin: update another user's role with safety rules."""
        if user_id == admin.id:
            logger.warning("Admin %s attempted to change own role", admin.id)
            raise UserPermissionError("Cannot change your own role")

        user = self._repo.get_by_id(user_id)
        if not user:
            logger.warning("Admin %s attempted to update non-existent user %s", admin.id, user_id)
            raise UserNotFoundError("User not found")

        if user.role == UserRole.ADMIN and role_update.role != UserRole.ADMIN:
            logger.warning("Admin %s attempted to demote admin %s", admin.id, user_id)
            raise UserPermissionError("Cannot change another admin's role")

        old_role = user.role
        user.role = role_update.role
        user.updated_at = datetime.now(UTC)

        try:
            updated = self._repo.save(user)
        except UserRepositoryError as e:
            logger.exception("Error updating user role for %s", user_id)
            raise UserServiceError("Failed to update user role") from e
        else:
            logger.warning(
                "Admin %s changed user %s role from %s to %s",
                admin.id,
                user_id,
                old_role,
                role_update.role,
            )
            return updated

    def delete_user(self, admin: User, user_id: UUID) -> None:
        """Admin: delete another user's account."""
        if user_id == admin.id:
            logger.warning("Admin %s attempted to delete own account", admin.id)
            raise UserPermissionError("Cannot delete your own account")

        user = self._repo.get_by_id(user_id)
        if not user:
            logger.warning("Admin %s attempted to delete non-existent user %s", admin.id, user_id)
            raise UserNotFoundError("User not found")

        try:
            self._repo.delete(user)
            logger.warning("Admin %s deleted user %s (%s)", admin.id, user_id, user.email)
        except UserRepositoryError as e:
            logger.exception("Error deleting user %s", user_id)
            raise UserServiceError("Failed to delete user") from e

    def verify_user_email(self, admin: User, user_id: UUID) -> User:
        """Admin: manually verify a user's email."""
        user = self._repo.get_by_id(user_id)
        if not user:
            logger.warning("Admin %s attempted to verify non-existent user %s", admin.id, user_id)
            raise UserNotFoundError("User not found")

        if user.email_verified:
            logger.info("Admin %s attempted to verify already verified user %s", admin.id, user_id)
            return user

        user.email_verified = True
        user.email_verification_token_hash = None
        user.email_verification_expires_at = None
        user.updated_at = datetime.now(UTC)

        try:
            updated = self._repo.save(user)
            logger.warning("Admin %s manually verified email for user %s (%s)", admin.id, user_id, user.email)
            return updated
        except UserRepositoryError as e:
            logger.exception("Error verifying email for user %s", user_id)
            raise UserServiceError("Failed to verify user email") from e

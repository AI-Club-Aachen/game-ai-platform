import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, List
from uuid import UUID

from app.api.repositories.user import UserRepository, UserRepositoryError
from app.core.security import hash_password, verify_password, validate_password_strength
from app.core.tokens import create_email_verification_token
from app.models.user import User, UserRole
from app.schemas.user import UserUpdate, UserRoleUpdate, PasswordChangeRequest

logger = logging.getLogger(__name__)


# --- Domain / application exceptions (non-HTTP) ---

class UserServiceError(Exception):
    """Base exception for user service errors."""
    pass


class UserNotFoundError(UserServiceError):
    """Raised when a user cannot be found."""
    pass


class UserConflictError(UserServiceError):
    """Raised when a uniqueness or similar conflict occurs (username/email)."""
    pass


class UserPermissionError(UserServiceError):
    """Raised when the current user is not allowed to perform an action."""
    pass


class UserValidationError(UserServiceError):
    """Raised when provided data is invalid (e.g. password rules)."""
    pass


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

        current_user.updated_at = datetime.now(timezone.utc)

        try:
            return self._repo.save(current_user)
        except UserRepositoryError as e:
            logger.error("Error updating user profile for %s: %s", current_user.id, e)
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
            current_user.updated_at = datetime.now(timezone.utc)
            self._repo.save(current_user)
            logger.info("Password changed successfully for user %s", current_user.id)
        except UserRepositoryError as e:
            logger.error("Error changing password for %s: %s", current_user.id, e)
            raise UserServiceError("Failed to change password") from e

    # --- Admin operations: list, get, role update, delete, verification email ---

    def list_users(
        self,
        skip: int,
        limit: int,
        role: Optional[UserRole] = None,
        email_verified: Optional[bool] = None,
    ) -> Tuple[List[User], int]:
        """Admin: list users with filters and pagination."""
        try:
            return self._repo.list_users(skip=skip, limit=limit, role=role, email_verified=email_verified)
        except UserRepositoryError as e:
            logger.error("Error listing users: %s", e)
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
        user.updated_at = datetime.now(timezone.utc)

        try:
            updated = self._repo.save(user)
            logger.warning(
                "Admin %s changed user %s role from %s to %s",
                admin.id,
                user_id,
                old_role,
                role_update.role,
            )
            return updated
        except UserRepositoryError as e:
            logger.error("Error updating user role for %s: %s", user_id, e)
            raise UserServiceError("Failed to update user role") from e

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
            logger.error("Error deleting user %s: %s", user_id, e)
            raise UserServiceError("Failed to delete user") from e

    def admin_send_verification_email(self, admin: User, user_id: UUID) -> User:
        """
        Admin: (re)issue an email verification token for a user.

        Note: this mirrors your current route behavior and only updates the token fields,
        leaving the actual email sending to a higher layer or another service.
        """
        user = self._repo.get_by_id(user_id)
        if not user:
            logger.warning("Admin %s attempted to email non-existent user %s", admin.id, user_id)
            raise UserNotFoundError("User not found")

        if user.email_verified:
            raise UserValidationError("User's email already verified")

        # Generate new verification token and update user
        plain_token, token_hash, expiry = create_email_verification_token()
        # Note: plain_token is not returned; email sending can use it if wired later.

        user.email_verification_token_hash = token_hash
        user.email_verification_expires_at = expiry
        user.updated_at = datetime.now(timezone.utc)

        try:
            updated = self._repo.save(user)
            logger.info("Admin %s set verification token for user %s", admin.id, user_id)
            return updated
        except UserRepositoryError as e:
            logger.error("Error setting verification token for user %s: %s", user_id, e)
            raise UserServiceError("Failed to send verification email") from e
import logging
from datetime import UTC, datetime, timedelta

from fastapi import BackgroundTasks

from app.api.repositories.user import UserRepository, UserRepositoryError
from app.api.services.email import EmailNotificationService
from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.core.tokens import (
    create_email_verification_token,
    create_password_reset_token,
    is_token_expired,
    safe_verify_token_hash,
)
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate


logger = logging.getLogger(__name__)


# --- Exceptions (domain/application, not HTTP) ---


class AuthServiceError(Exception):
    """Base exception for auth service errors."""


class AuthValidationError(AuthServiceError):
    """Input or password/token validation issue."""


class AuthConflictError(AuthServiceError):
    """Uniqueness or state conflict (e.g. already registered)."""


class AuthNotFoundError(AuthServiceError):
    """User or token not found."""


class AuthForbiddenError(AuthServiceError):
    """Action not allowed due to user state (e.g. unverified)."""


class AuthService:
    """
    Application service for authentication-related flows.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        email_notifications: EmailNotificationService,
    ) -> None:
        self._users = user_repo
        self._emails = email_notifications

    # --- Registration ---

    def register(
        self,
        user_data: UserCreate,
        background_tasks: BackgroundTasks,
    ) -> tuple[User, str]:
        """
        Register a new user with email verification.

        Returns the created user and the plain verification token.
        """
        # Validate and hash password
        try:
            password_hash = hash_password(user_data.password)
        except ValueError as e:
            logger.warning("Password validation failed for registration: %s", e)
            raise AuthValidationError(str(e)) from e

        # Username uniqueness (case-insensitive)
        username_lower = user_data.username.lower()
        existing_user = self._users.get_by_username_ci(username_lower)
        if existing_user:
            if existing_user.email_verified:
                logger.warning(
                    "Registration attempt with verified username: %s",
                    user_data.username,
                )
                raise AuthConflictError("Username already registered")
            # Delete unverified account to allow re-registration
            logger.info(
                "Deleting unverified account for re-registration: %s",
                existing_user.id,
            )
            try:
                self._users.delete(existing_user)
            except UserRepositoryError as e:
                logger.exception("Error deleting unverified user during re-registration")
                raise AuthServiceError(
                    "Failed to clean up previous registration",
                ) from e

        # Email uniqueness (case-insensitive)
        email_lower = str(user_data.email).lower()
        existing_user = self._users.get_by_email_ci(email_lower)
        if existing_user:
            if existing_user.email_verified:
                logger.warning(
                    "Registration attempt with verified email: %s",
                    user_data.email,
                )
                raise AuthConflictError("Email already registered")
            logger.info(
                "Deleting unverified account for re-registration: %s",
                existing_user.id,
            )
            try:
                self._users.delete(existing_user)
            except UserRepositoryError as e:
                logger.exception("Error deleting unverified user by email")
                raise AuthServiceError(
                    "Failed to clean up previous registration",
                ) from e

        # Generate verification token
        plain_token, token_hash, expiry = create_email_verification_token()

        # Create user
        now = datetime.now(UTC)
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            role=UserRole.GUEST,
            email_verified=False,
            email_verification_token_hash=token_hash,
            email_verification_expires_at=expiry,
            created_at=now,
            updated_at=now,
        )

        try:
            user = self._users.save(user)
        except UserRepositoryError as e:
            logger.exception("Database error during registration")
            raise AuthServiceError("Failed to create user account") from e

        # Send verification email in background
        background_tasks.add_task(
            self._emails.send_verification_email,
            to_email=user.email,
            username=user.username,
            token=plain_token,
        )

        logger.info("New user registered: %s (ID: %s)", user.email, user.id)
        return user, plain_token

    # --- Login ---

    def login(self, login_request: LoginRequest) -> tuple[str, User]:
        """
        Login with email and password.

        Returns (access_token, user).
        """
        email_lower = str(login_request.email).lower()
        user = self._users.get_by_email_ci(email_lower)

        if not user or not verify_password(login_request.password, user.password_hash):
            logger.warning("Failed login attempt: %s", login_request.email)
            raise AuthValidationError("Invalid email or password")

        if not user.email_verified:
            logger.warning("Login attempt with unverified email: %s", user.email)
            raise AuthForbiddenError(
                "Email not verified. Check your inbox for verification link.",
            )

        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "role": user.role.value,
            },
            expires_delta=timedelta(hours=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS),
        )

        logger.info("User logged in: %s (ID: %s)", user.email, user.id)
        return access_token, user

    # --- Email verification ---

    def verify_email(self, token: str) -> User:
        """
        Verify email address with a token.
        """
        users = self._users.get_unverified_with_verification_tokens()
        matched_user: User | None = None
        for u in users:
            if safe_verify_token_hash(token, u.email_verification_token_hash):
                matched_user = u
                break

        if not matched_user:
            logger.warning("Invalid email verification token provided")
            raise AuthValidationError("Invalid verification token")

        if is_token_expired(matched_user.email_verification_expires_at):
            logger.warning("Expired verification token used: %s", matched_user.email)
            matched_user.email_verification_token_hash = None
            matched_user.email_verification_expires_at = None
            matched_user.updated_at = datetime.now(UTC)
            try:
                self._users.save(matched_user)
            except UserRepositoryError:
                logger.exception("Error clearing expired verification token")
            raise AuthValidationError(
                "Verification token expired. Request a new one.",
            )

        matched_user.email_verified = True
        matched_user.email_verification_token_hash = None
        matched_user.email_verification_expires_at = None
        matched_user.updated_at = datetime.now(UTC)

        try:
            user = self._users.save(matched_user)
        except UserRepositoryError as e:
            logger.exception("Database error during email verification")
            raise AuthServiceError("Failed to verify email") from e

        logger.info("Email verified: %s (ID: %s)", user.email, user.id)
        return user

    def resend_verification_for_user(
        self,
        current_user: User,
        background_tasks: BackgroundTasks,
    ) -> None:
        """
        Resend email verification link to the currently authenticated user.
        """
        if current_user.email_verified:
            logger.warning(
                "Resend verification requested by verified user: %s",
                current_user.email,
            )
            raise AuthValidationError("Email already verified")

        try:
            plain_token, token_hash, expiry = create_email_verification_token()
            current_user.email_verification_token_hash = token_hash
            current_user.email_verification_expires_at = expiry
            current_user.updated_at = datetime.now(UTC)
            self._users.save(current_user)

            background_tasks.add_task(
                self._emails.send_verification_email,
                to_email=current_user.email,
                username=current_user.username,
                token=plain_token,
            )

            logger.info("Verification email resent to: %s", current_user.email)
        except UserRepositoryError as e:
            logger.exception("Error resending verification email")
            raise AuthServiceError("Failed to resend verification email") from e

    # --- Password reset request ---

    def request_password_reset(
        self,
        email: str,
        background_tasks: BackgroundTasks,
    ) -> None:
        """
        Request password reset via email.

        Always returns successfully (to avoid email enumeration),
        but may log internal errors.
        """
        email_lower = email.lower()
        user = self._users.get_by_email_ci(email_lower)

        if not user:
            logger.info(f"User {email_lower} not found. Simply ignore request")
            return

        try:
            plain_token, token_hash, expiry = create_password_reset_token()

            user.password_reset_token_hash = token_hash
            user.password_reset_expires_at = expiry
            user.updated_at = datetime.now(UTC)
            self._users.save(user)

            background_tasks.add_task(
                self._emails.send_password_reset_email,
                to_email=user.email,
                username=user.username,
                token=plain_token,
            )

            logger.info("Password reset requested for: %s", user.email)
        except UserRepositoryError:
            logger.exception("Error processing password reset")
        except Exception:
            logger.exception("Unexpected error processing password reset")

    # --- Password reset confirm ---

    def reset_password(self, token: str, new_password: str) -> User:
        """
        Reset password using a token and new password.
        """
        try:
            validate_password_strength(new_password)
            password_hash = hash_password(new_password)
        except ValueError as e:
            logger.warning("Password validation failed during reset: %s", e)
            raise AuthValidationError(str(e)) from e

        users = self._users.get_with_active_reset_tokens()
        matched_user: User | None = None
        for u in users:
            if safe_verify_token_hash(token, u.password_reset_token_hash):
                matched_user = u
                break

        if not matched_user:
            logger.warning("Invalid password reset token provided")
            raise AuthValidationError("Invalid password reset token")

        if is_token_expired(matched_user.password_reset_expires_at):
            logger.warning("Expired reset token used: %s", matched_user.email)
            matched_user.password_reset_token_hash = None
            matched_user.password_reset_expires_at = None
            matched_user.updated_at = datetime.now(UTC)
            try:
                self._users.save(matched_user)
            except UserRepositoryError:
                logger.exception("Error clearing expired reset token")
            raise AuthValidationError(
                "Password reset token expired. Request a new one.",
            )

        matched_user.password_hash = password_hash
        matched_user.password_reset_token_hash = None
        matched_user.password_reset_expires_at = None
        matched_user.updated_at = datetime.now(UTC)

        try:
            user = self._users.save(matched_user)
        except UserRepositoryError as e:
            logger.exception("Database error during password reset")
            raise AuthServiceError("Failed to reset password") from e

        logger.info("Password reset successful: %s (ID: %s)", user.email, user.id)
        return user

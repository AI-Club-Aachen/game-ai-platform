import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import BackgroundTasks

from app.api.repositories.user import UserRepository, UserRepositoryError
from app.api.services.email import EmailNotificationService
from app.core.config import settings
from app.core.security import (
    create_access_token,
    dummy_verify_password,
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

        On a collision with an existing **unverified** account, the pending account
        is NOT deleted (L-6 pre-hijack guard): its verification email is re-issued
        and the submitted password is discarded, so an attacker cannot take over a
        pending registration by re-registering its username/email.
        """
        # Validate and hash password (also flattens timing for collisions below).
        try:
            password_hash = hash_password(user_data.password)
        except ValueError as e:
            logger.warning("Password validation failed for registration: %s", e)
            raise AuthValidationError(str(e)) from e

        # Username uniqueness (case-insensitive)
        existing_user = self._users.get_by_username_ci(user_data.username.lower())
        if existing_user:
            if existing_user.email_verified:
                logger.warning("Registration attempt with verified username: %s", user_data.username)
                raise AuthConflictError("Username already registered")
            return self._reissue_pending_registration(existing_user, background_tasks)

        # Email uniqueness (case-insensitive)
        existing_user = self._users.get_by_email_ci(str(user_data.email).lower())
        if existing_user:
            if existing_user.email_verified:
                logger.warning("Registration attempt with verified email: %s", user_data.email)
                raise AuthConflictError("Email already registered")
            return self._reissue_pending_registration(existing_user, background_tasks)

        return self._create_user(user_data, password_hash, background_tasks)

    def _create_user(
        self,
        user_data: UserCreate,
        password_hash: str,
        background_tasks: BackgroundTasks,
    ) -> tuple[User, str]:
        """Persist a brand-new guest account and send its verification email."""
        bypass_verification = settings.BYPASS_EMAIL_VERIFICATION and not settings.is_production

        plain_token = "bypassed"  # noqa: S105
        token_hash = None
        expiry = None
        if not bypass_verification:
            plain_token, token_hash, expiry = create_email_verification_token()

        now = datetime.now(UTC)
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            role=UserRole.GUEST,
            email_verified=bypass_verification,
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

        if not bypass_verification:
            background_tasks.add_task(
                self._emails.send_verification_email,
                to_email=user.email,
                username=user.username,
                token=plain_token,
            )
        else:
            logger.info("Skipping email verification for user %s due to dev bypass", user.email)

        logger.info("New user registered: %s (ID: %s)", user.email, user.id)
        return user, plain_token

    def _reissue_pending_registration(
        self,
        user: User,
        background_tasks: BackgroundTasks,
    ) -> tuple[User, str]:
        """Re-send verification to an existing UNVERIFIED account on a registration
        collision instead of deleting/overwriting it (L-6 pre-hijack guard).

        The account's credentials are left untouched; only a fresh verification token
        is issued. The response is indistinguishable from a normal registration.
        """
        plain_token, token_hash, expiry = create_email_verification_token()
        user.email_verification_token_hash = token_hash
        user.email_verification_expires_at = expiry
        user.updated_at = datetime.now(UTC)

        try:
            user = self._users.save(user)
        except UserRepositoryError as e:
            logger.exception("Error re-issuing verification for pending registration")
            raise AuthServiceError("Failed to create user account") from e

        background_tasks.add_task(
            self._emails.send_verification_email,
            to_email=user.email,
            username=user.username,
            token=plain_token,
        )
        logger.info("Re-issued verification for pending account on re-registration: %s", user.id)
        return user, plain_token

    # --- Login ---

    def login(self, login_request: LoginRequest) -> tuple[str, User]:
        """
        Login with email and password.

        Returns (access_token, user).
        """
        email_lower = str(login_request.email).lower()
        user = self._users.get_by_email_ci(email_lower)

        # Uniform failure for unknown user vs wrong password (L-6): a missing user
        # runs a dummy hash so timing matches, and both raise the same 401. The
        # "email not verified" signal is only surfaced AFTER a correct password,
        # so it cannot be used to enumerate registered-but-unverified accounts.
        if user is None:
            dummy_verify_password(login_request.password)
            logger.warning("Failed login attempt (unknown user): %s", login_request.email)
            raise AuthValidationError("Invalid email or password")

        if not verify_password(login_request.password, user.password_hash):
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
                # Session-invalidation claim (M-11): tokens become stale when the
                # user's token_version is bumped on password change/reset.
                "token_version": user.token_version,
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

    def admin_resend_verification_email(
        self,
        admin: User,
        user_id: UUID,
        background_tasks: BackgroundTasks,
    ) -> User:
        """
        Admin: (re)issue an email verification token for a user and send the email.
        """
        user = self._users.get_by_id(user_id)
        if not user:
            logger.warning("Admin %s attempted to email non-existent user %s", admin.id, user_id)
            raise AuthNotFoundError("User not found")

        if user.email_verified:
            raise AuthValidationError("User's email already verified")

        # Generate new verification token and update user
        plain_token, token_hash, expiry = create_email_verification_token()

        user.email_verification_token_hash = token_hash
        user.email_verification_expires_at = expiry
        user.updated_at = datetime.now(UTC)

        try:
            updated = self._users.save(user)
        except UserRepositoryError as e:
            logger.exception("Error setting verification token for user %s", user_id)
            raise AuthServiceError("Failed to send verification email") from e

        # Send verification email in background
        background_tasks.add_task(
            self._emails.send_verification_email,
            to_email=updated.email,
            username=updated.username,
            token=plain_token,
        )

        logger.info("Admin %s triggered verification email for user %s", admin.id, user_id)
        return updated

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
        # Invalidate every JWT issued before this reset (M-11) — critical when
        # recovering a compromised account.
        matched_user.token_version += 1
        matched_user.updated_at = datetime.now(UTC)

        try:
            user = self._users.save(matched_user)
        except UserRepositoryError as e:
            logger.exception("Database error during password reset")
            raise AuthServiceError("Failed to reset password") from e

        logger.info("Password reset successful: %s (ID: %s)", user.email, user.id)
        return user

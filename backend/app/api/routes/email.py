"""Email management routes with secure token verification and rate limiting"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlmodel import Session, select

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_session, get_current_user, CurrentUser
from app.core.tokens import (
    create_email_verification_token,
    create_password_reset_token,
    safe_verify_token_hash,
    is_token_expired,
)
from app.core.email import email_service
from app.core.config import settings
from app.models.user import User
from app.schemas.email import (
    EmailVerificationRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    ResendVerificationEmailRequest,
)
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/email")


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
@limiter.limit("10/day")
async def resend_verification_email(
    request: Request,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """
    Resend email verification link to current user.

    Rate limited: 10 per day per user (by IP).
    """

    if user.email_verified:
        logger.warning(f"Resend verification requested by verified user: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified",
        )

    try:
        plain_token, token_hash, expiry = create_email_verification_token()

        user.email_verification_token_hash = token_hash
        user.email_verification_expires_at = expiry
        user.updated_at = datetime.now(timezone.utc)
        session.add(user)
        session.commit()

        background_tasks.add_task(
            email_service.send_verification_email,
            to_email=user.email,
            username=user.username,
            token=plain_token,
        )

        logger.info(f"Verification email resent to: {user.email}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error resending verification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email",
        )

    return {"message": "Verification email sent. Check your inbox."}


@router.post("/verify-email", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    verification_request: EmailVerificationRequest,
    session: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    """Verify email address with token sent via email."""

    if not verification_request.token or len(verification_request.token) < 16:
        logger.warning("Invalid email verification token format")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token format",
        )

    # Query unverified users with verification tokens
    statement = select(User).where(
        User.email_verified == False,
        User.email_verification_token_hash.isnot(None),
    )

    users = session.exec(statement).all()

    if not users:
        logger.debug("No unverified users found")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    # Find matching token using constant-time comparison
    matched_user = None
    for u in users:
        if safe_verify_token_hash(verification_request.token, u.email_verification_token_hash):
            matched_user = u
            break

    if not matched_user:
        logger.warning("Invalid email verification token provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    # Check token expiry
    if is_token_expired(matched_user.email_verification_expires_at):
        logger.info(f"Expired verification token used for: {matched_user.email}")
        matched_user.email_verification_token_hash = None
        matched_user.email_verification_expires_at = None
        matched_user.updated_at = datetime.now(timezone.utc)
        try:
            session.add(matched_user)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error clearing expired token: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token expired. Request a new one.",
        )

    # Mark email as verified and clear token
    matched_user.email_verified = True
    matched_user.email_verification_token_hash = None
    matched_user.email_verification_expires_at = None
    matched_user.updated_at = datetime.now(timezone.utc)

    try:
        session.add(matched_user)
        session.commit()
        session.refresh(matched_user)
    except Exception as e:
        session.rollback()
        logger.error(f"Database error during email verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email",
        )

    logger.info(f"Email verified successfully: {matched_user.email} (ID: {matched_user.id})")
    return matched_user


@router.post("/request-password-reset", status_code=status.HTTP_200_OK)
@limiter.limit("10/hour")
async def request_password_reset(
    request: Request,
    password_reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """
    Request password reset via email.

    Rate limited: 10 per hour per IP.
    """

    email_lower = password_reset_request.email.lower()
    statement = select(User).where(User.email.ilike(email_lower))
    user = session.exec(statement).first()

    # Always return same message to prevent email enumeration
    if user:
        try:
            plain_token, token_hash, expiry = create_password_reset_token()

            user.password_reset_token_hash = token_hash
            user.password_reset_expires_at = expiry
            user.updated_at = datetime.now(timezone.utc)
            session.add(user)
            session.commit()

            background_tasks.add_task(
                email_service.send_password_reset_email,
                to_email=user.email,
                username=user.username,
                token=plain_token,
            )

            logger.info(f"Password reset requested for: {user.email}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error processing password reset request: {e}")

    return {
        "message": "If email exists, password reset link will be sent",
        "details": "Check your inbox for reset instructions",
    }


@router.post("/reset-password", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    password_reset_request: PasswordResetConfirm,
    session: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    """Reset password with token sent via email."""

    if not password_reset_request.token or len(password_reset_request.token) < 16:
        logger.warning("Invalid password reset token format")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token format",
        )

    # Validate new password strength
    try:
        from app.core.security import _validate_password_strength, hash_password
        _validate_password_strength(password_reset_request.new_password)
        password_hash = hash_password(password_reset_request.new_password)
    except ValueError as e:
        logger.warning(f"Password validation failed during reset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Query users with active reset tokens
    statement = select(User).where(
        User.password_reset_token_hash.isnot(None)
    )

    users = session.exec(statement).all()

    if not users:
        logger.debug("No users with active reset tokens found")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token",
        )

    # Find matching token using constant-time comparison
    matched_user = None
    for u in users:
        if safe_verify_token_hash(password_reset_request.token, u.password_reset_token_hash):
            matched_user = u
            break

    if not matched_user:
        logger.warning("Invalid password reset token provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token",
        )

    # Check token expiry
    if is_token_expired(matched_user.password_reset_expires_at):
        logger.info(f"Expired reset token used for: {matched_user.email}")
        matched_user.password_reset_token_hash = None
        matched_user.password_reset_expires_at = None
        matched_user.updated_at = datetime.now(timezone.utc)
        try:
            session.add(matched_user)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error clearing expired reset token: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token expired. Request a new one.",
        )

    # Update password
    matched_user.password_hash = password_hash
    matched_user.password_reset_token_hash = None
    matched_user.password_reset_expires_at = None
    matched_user.updated_at = datetime.now(timezone.utc)

    try:
        session.add(matched_user)
        session.commit()
        session.refresh(matched_user)
    except Exception as e:
        session.rollback()
        logger.error(f"Database error during password reset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password",
        )

    logger.info(f"Password reset successful: {matched_user.email} (ID: {matched_user.id})")
    return matched_user


@router.get("/verification-status", response_model=dict)
async def check_verification_status(
    user: CurrentUser,
) -> dict:
    """Check current user's email verification status."""
    return {
        "email": user.email,
        "email_verified": user.email_verified,
        "verification_expires_at": user.email_verification_expires_at,
        "can_resend": not user.email_verified,
    }

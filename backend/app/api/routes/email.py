"""Email management routes with secure token verification and rate limiting"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import (
    CurrentAdmin,
    CurrentUser,
    get_auth_service,
)
from app.api.services.auth import (
    AuthNotFoundError,
    AuthService,
    AuthServiceError,
    AuthValidationError,
)
from app.schemas.email import (
    AdminEmailVerificationResponse,
    EmailVerificationRequest,
    EmailVerificationResponse,
    VerificationStatusResponse,
)
from app.schemas.user import UserResponse


logger = logging.getLogger(__name__)

# Minimum length for email verification tokens
MIN_TOKEN_LENGTH = 16
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/email")


@router.post("/resend-verification", status_code=status.HTTP_200_OK, response_model=EmailVerificationResponse)
@limiter.limit("10/day")
async def resend_verification_email(
    request: Request,  # noqa: ARG001
    user: CurrentUser,
    background_tasks: BackgroundTasks,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> EmailVerificationResponse:
    """
    Resend email verification link to current user.

    Rate limited: 10 per day per user (by IP).
    """
    try:
        auth_service.resend_verification_for_user(
            current_user=user,
            background_tasks=background_tasks,
        )
    except AuthValidationError as e:
        # Email already verified
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except AuthServiceError as e:
        logger.exception("Error resending verification email for %s", user.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email",
        ) from e

    return EmailVerificationResponse(message="Verification email sent. Check your inbox.")


@router.post(
    "/{user_id}/resend-verification", status_code=status.HTTP_200_OK, response_model=AdminEmailVerificationResponse
)
@limiter.limit("1000/hour")
async def admin_resend_verification_email(
    request: Request,  # noqa: ARG001
    user_id: UUID,
    admin: CurrentAdmin,
    background_tasks: BackgroundTasks,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AdminEmailVerificationResponse:
    """Admin: Resend verification email to user."""
    try:
        user = auth_service.admin_resend_verification_email(
            admin=admin,
            user_id=user_id,
            background_tasks=background_tasks,
        )
    except AuthNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except AuthValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except AuthServiceError as e:
        logger.exception("Error sending verification email for user %s by admin %s", user_id, admin.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        ) from e

    logger.info("Admin %s triggered verification email for user %s", admin.id, user_id)

    return AdminEmailVerificationResponse(
        message="Verification email sent",
        user_id=str(user.id),
    )


@router.post("/verify-email", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def verify_email(
    request: Request,  # noqa: ARG001
    verification_request: EmailVerificationRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Verify email address with token sent via email."""
    # Optional extra format check, though the schema already enforces min_length
    if not verification_request.token or len(verification_request.token) < MIN_TOKEN_LENGTH:
        logger.warning("Invalid email verification token format")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token format",
        )

    try:
        user = auth_service.verify_email(verification_request.token)
        return UserResponse.model_validate(user)
    except AuthValidationError as e:
        # Invalid token or expired token
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except AuthServiceError as e:
        logger.exception("Error verifying email")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email",
        ) from e


@router.get("/verification-status", response_model=VerificationStatusResponse)
async def check_verification_status(
    user: CurrentUser,
) -> VerificationStatusResponse:
    """Check current user's email verification status."""
    return VerificationStatusResponse(
        email=user.email,
        email_verified=user.email_verified,
        verification_expires_at=user.email_verification_expires_at,
        can_resend=not user.email_verified,
    )

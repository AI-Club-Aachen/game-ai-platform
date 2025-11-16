"""Email management routes with secure token verification and rate limiting"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import (
    CurrentUser,
    get_auth_service,
)
from app.api.services.auth import (
    AuthService,
    AuthServiceError,
    AuthValidationError,
)
from app.schemas.email import (
    EmailVerificationRequest
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
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
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
        logger.error("Error resending verification email for %s: %s", user.email, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email",
        ) from e

    return {"message": "Verification email sent. Check your inbox."}


@router.post("/verify-email", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    verification_request: EmailVerificationRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Verify email address with token sent via email."""
    # Optional extra format check, though the schema already enforces min_length
    if not verification_request.token or len(verification_request.token) < 16:
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
        logger.error("Error verifying email: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email",
        ) from e


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
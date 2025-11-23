"""Authentication routes with security best practices and rate limiting"""

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_auth_service
from app.api.services.auth import (
    AuthConflictError,
    AuthForbiddenError,
    AuthService,
    AuthServiceError,
    AuthValidationError,
)
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import UserCreate, UserResponse


logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth")


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=dict)
@limiter.limit("20/hour")
async def register(
    request: Request,
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    """
    Register new user with email verification.

    Allows re-registration if previous account is unverified.
    Rate limited: 20 registrations per hour per IP.
    """
    try:
        user, _plain_token = auth_service.register(
            user_data=user_data,
            background_tasks=background_tasks,
        )
    except AuthValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except AuthConflictError as e:
        # Username/email already taken and verified
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except AuthServiceError as e:
        logger.error("Database error during registration: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account",
        ) from e

    return {
        "message": "Registration successful. Check your email for verification link.",
        "user_id": str(user.id),
        "email": user.email,
    }


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@limiter.limit("30/minute;200/day")
async def login(
    request: Request,
    login_request: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    """
    Login with email and password.

    Rate limited: 30 per minute, 200 per day per IP.
    """
    try:
        access_token, user = auth_service.login(login_request)
    except AuthValidationError as e:
        # Invalid email or password
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except AuthForbiddenError as e:
        # Email not verified
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except AuthServiceError as e:
        logger.error("Error during login: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to login",
        ) from e

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.id),
        username=user.username,
    )


@router.post("/request-password-reset", status_code=status.HTTP_200_OK)
@limiter.limit("10/hour")
async def request_password_reset(
    request: Request,
    email: str,
    background_tasks: BackgroundTasks,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    """
    Request password reset via email.

    Rate limited: 10 per hour per IP.
    """
    # Always return same message to prevent email enumeration
    auth_service.request_password_reset(
        email=email,
        background_tasks=background_tasks,
    )
    return {"message": "If email exists, password reset link will be sent"}


@router.post("/reset-password", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    token: str,
    new_password: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Reset password with token sent via email."""
    try:
        user = auth_service.reset_password(token=token, new_password=new_password)
    except AuthValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except AuthServiceError as e:
        logger.error("Error resetting password: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password",
        ) from e

    return UserResponse.model_validate(user)

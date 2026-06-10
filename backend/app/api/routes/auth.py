"""Authentication routes with security best practices and rate limiting"""

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from app.api.deps import get_auth_service
from app.api.services.auth import (
    AuthConflictError,
    AuthForbiddenError,
    AuthService,
    AuthServiceError,
    AuthValidationError,
)
from app.core.config import settings
from app.core.rate_limit import limiter
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordResetRequestResponse,
    RegistrationResponse,
)
from app.schemas.user import UserCreate, UserResponse


logger = logging.getLogger(__name__)

router = APIRouter()


# POST /api/v1/auth/register
@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegistrationResponse)
@limiter.limit(lambda: settings.RATE_LIMIT_REGISTER)
async def register(
    request: Request,  # noqa: ARG001
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> RegistrationResponse:
    """
    Register new user with email verification.

    Allows re-registration if previous account is unverified.
    Rate limited per RATE_LIMIT_REGISTER.
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
        logger.exception("Database error during registration")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account",
        ) from e

    return RegistrationResponse(
        message="Registration successful. Check your email for verification link.",
        user_id=str(user.id),
        email=user.email,
    )


# POST /api/v1/auth/login
@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@limiter.limit(lambda: settings.RATE_LIMIT_LOGIN)
async def login(
    request: Request,  # noqa: ARG001
    login_request: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    """
    Login with email and password.

    Rate limited per RATE_LIMIT_LOGIN.
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
        logger.exception("Error during login")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to login",
        ) from e

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",  # noqa: S106
        user_id=str(user.id),
        username=user.username,
        role=user.role.value,
    )


# POST /api/v1/auth/request-password-reset
@router.post("/request-password-reset", status_code=status.HTTP_200_OK, response_model=PasswordResetRequestResponse)
@limiter.limit(lambda: settings.RATE_LIMIT_EMAIL_TOKEN)
async def request_password_reset(
    request: Request,  # noqa: ARG001
    email: str,
    background_tasks: BackgroundTasks,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> PasswordResetRequestResponse:
    """
    Request password reset via email.

    Rate limited per RATE_LIMIT_EMAIL_TOKEN.
    """
    # Always return same message to prevent email enumeration
    auth_service.request_password_reset(
        email=email,
        background_tasks=background_tasks,
    )
    return PasswordResetRequestResponse(message="If email exists, password reset link will be sent")


# POST /api/v1/auth/reset-password
@router.post("/reset-password", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit(lambda: settings.RATE_LIMIT_EMAIL_TOKEN)
async def reset_password(
    request: Request,  # noqa: ARG001
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
        logger.exception("Error resetting password")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password",
        ) from e

    return UserResponse.model_validate(user)

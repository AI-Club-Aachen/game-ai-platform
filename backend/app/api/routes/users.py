"""User management routes with security, role-based access, and rate limiting"""

import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import (
    get_user_service,
    CurrentUser,
    CurrentAdmin,
)
from app.api.services.user import (
    UserService,
    UserServiceError,
    UserNotFoundError,
    UserConflictError,
    UserPermissionError,
    UserValidationError,
)
from app.models.user import UserRole
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    UserRoleUpdate,
    PasswordChangeRequest,
)

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/users")


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    user: CurrentUser,
) -> UserResponse:
    """Get current authenticated user's profile."""
    return user


@router.patch("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_current_user_profile(
    user_update: UserUpdate,
    user: CurrentUser,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Update current user's profile (username or email)."""
    try:
        updated_user = user_service.update_current_user_profile(
            current_user=user,
            user_update=user_update,
        )
        return UserResponse.model_validate(updated_user)
    except UserConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except UserValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except UserServiceError as e:
        logger.error("Error updating user profile %s: %s", user.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        ) from e


@router.post("/change-password", response_model=dict, status_code=status.HTTP_200_OK)
@limiter.limit("15/day")
async def change_password(
    request: Request,
    password_request: PasswordChangeRequest,
    user: CurrentUser,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> dict:
    """
    Change current user's password.

    Rate limited: 15 changes per day per IP.
    """
    try:
        user_service.change_password(current_user=user, password_request=password_request)
        return {"message": "Password changed successfully"}
    except UserValidationError as e:
        # Incorrect current password, weak password, or same as old
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except UserServiceError as e:
        logger.error("Error changing password for user %s: %s", user.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        ) from e


# Admin endpoints with higher rate limits (1000/hour)
@router.get("/", response_model=dict, status_code=status.HTTP_200_OK)
@limiter.limit("1000/hour")
async def list_users(
    request: Request,
    admin: CurrentAdmin,
    user_service: Annotated[UserService, Depends(get_user_service)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    role: Annotated[Optional[UserRole], Query()] = None,
    email_verified: Annotated[Optional[bool], Query()] = None,
) -> dict:
    """Admin: List all users with filtering and pagination."""
    try:
        users, total = user_service.list_users(
            skip=skip,
            limit=limit,
            role=role,
            email_verified=email_verified,
        )
    except UserServiceError as e:
        logger.error("Error listing users for admin %s: %s", admin.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users",
        ) from e

    logger.info(
        "Admin %s listed %d users (skip=%d, limit=%d)",
        admin.id,
        len(users),
        skip,
        limit,
    )

    return {
        "data": users,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("1000/hour")
async def get_user_by_id(
    request: Request,
    user_id: UUID,
    admin: CurrentAdmin,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Admin: Get user details by ID."""
    try:
        user = user_service.get_user_by_id(user_id)
    except UserNotFoundError as e:
        logger.warning("Admin %s attempted to access non-existent user %s", admin.id, user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except UserServiceError as e:
        logger.error("Error fetching user %s for admin %s: %s", user_id, admin.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user",
        ) from e

    logger.info("Admin %s viewed user %s", admin.id, user_id)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}/role", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("1000/hour")
async def update_user_role(
    request: Request,
    user_id: UUID,
    role_update: UserRoleUpdate,
    admin: CurrentAdmin,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Admin: Update user's role."""
    try:
        user = user_service.update_user_role(
            admin=admin,
            user_id=user_id,
            role_update=role_update,
        )
        return UserResponse.model_validate(user)
    except UserPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except UserServiceError as e:
        logger.error("Error updating role for user %s by admin %s: %s", user_id, admin.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role",
        ) from e


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("1000/hour")
async def delete_user(
    request: Request,
    user_id: UUID,
    admin: CurrentAdmin,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    """Admin: Delete user account."""
    try:
        user_service.delete_user(admin=admin, user_id=user_id)
    except UserPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except UserServiceError as e:
        logger.error("Error deleting user %s by admin %s: %s", user_id, admin.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        ) from e


@router.post("/{user_id}/send-verification-email", status_code=status.HTTP_200_OK)
@limiter.limit("1000/hour")
async def admin_send_verification_email(
    request: Request,
    user_id: UUID,
    admin: CurrentAdmin,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> dict:
    """Admin: Send verification email to user (resend)."""
    try:
        user = user_service.admin_send_verification_email(admin=admin, user_id=user_id)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except UserValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except UserServiceError as e:
        logger.error("Error sending verification email for user %s by admin %s: %s", user_id, admin.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        ) from e

    logger.info("Admin %s triggered verification email for user %s", admin.id, user_id)

    return {
        "message": "Verification email sent",
        "user_id": str(user.id),
    }
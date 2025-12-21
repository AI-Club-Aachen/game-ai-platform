"""User management routes with security, role-based access, and rate limiting"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import (
    CurrentAdmin,
    CurrentUser,
    get_user_service,
)
from app.api.services.user import (
    UserConflictError,
    UserNotFoundError,
    UserPermissionError,
    UserService,
    UserServiceError,
    UserValidationError,
)
from app.models.user import UserRole
from app.schemas.user import (
    ChangePasswordResponse,
    PasswordChangeRequest,
    UserListResponse,
    UserResponse,
    UserRoleList,
    UserRoleUpdate,
    UserUpdate,
)


logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/users")


@router.get("/roles", response_model=UserRoleList, status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def list_roles(
    request: Request,  # noqa: ARG001
    # We allow any authenticated user to see available roles, or even public if needed.
    # For now, let's keep it open or maybe just require auth?
    # Given it's a "platform", knowing roles isn't super sensitive, but usually you'd be logged in.
    # Let's make it authenticated to be consistent with /me.
    user: CurrentUser,
) -> UserRoleList:
    """List all available user roles."""
    return UserRoleList(roles=list(UserRole))


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def get_current_user_profile(
    request: Request,  # noqa: ARG001
    user: CurrentUser,
) -> UserResponse:
    """Get current authenticated user's profile."""
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("15/day")
async def update_current_user_profile(
    request: Request,  # noqa: ARG001
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
        logger.exception("Error updating user profile %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        ) from e


@router.post("/change-password", response_model=ChangePasswordResponse, status_code=status.HTTP_200_OK)
@limiter.limit("15/day")
async def change_password(
    request: Request,  # noqa: ARG001
    password_request: PasswordChangeRequest,
    user: CurrentUser,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> ChangePasswordResponse:
    """
    Change current user's password.

    Rate limited: 15 changes per day per IP.
    """
    try:
        user_service.change_password(current_user=user, password_request=password_request)
    except UserValidationError as e:
        # Incorrect current password, weak password, or same as old
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except UserServiceError as e:
        logger.exception("Error changing password for user %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        ) from e
    else:
        return ChangePasswordResponse(message="Password changed successfully")


# Admin endpoints with higher rate limits (1000/hour)
@router.get("/", response_model=UserListResponse, status_code=status.HTTP_200_OK)
@limiter.limit("1000/hour")
async def list_users(
    request: Request,  # noqa: ARG001
    admin: CurrentAdmin,
    user_service: Annotated[UserService, Depends(get_user_service)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    role: Annotated[UserRole | None, Query()] = None,
    email_verified: Annotated[bool | None, Query()] = None,
) -> UserListResponse:
    """Admin: List all users with filtering and pagination."""
    try:
        users, total = user_service.list_users(
            skip=skip,
            limit=limit,
            role=role,
            email_verified=email_verified,
        )
    except UserServiceError as e:
        logger.exception("Error listing users for admin %s", admin.id)
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

    return UserListResponse(
        data=[UserResponse.model_validate(u) for u in users],
        total=total,
        skip=skip,
        limit=limit,
    )

@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("1000/hour")
async def get_user_by_id(
    request: Request,  # noqa: ARG001
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
        logger.exception("Error fetching user %s for admin %s", user_id, admin.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user",
        ) from e

    logger.info("Admin %s viewed user %s", admin.id, user_id)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}/role", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("1000/hour")
async def update_user_role(
    request: Request,  # noqa: ARG001
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
        logger.exception("Error updating role for user %s by admin %s", user_id, admin.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role",
        ) from e


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("1000/hour")
async def delete_user(
    request: Request,  # noqa: ARG001
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
        logger.exception("Error deleting user %s by admin %s", user_id, admin.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        ) from e


@router.patch("/{user_id}/verify-email", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("1000/hour")
async def verify_user_email(
    request: Request,  # noqa: ARG001
    user_id: UUID,
    admin: CurrentAdmin,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Admin: Manually verify a user's email."""
    try:
        user = user_service.verify_user_email(admin=admin, user_id=user_id)
        return UserResponse.model_validate(user)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except UserServiceError as e:
        logger.exception("Error verifying email for user %s by admin %s", user_id, admin.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify user email",
        ) from e

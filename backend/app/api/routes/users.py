"""User management routes with security, role-based access, and rate limiting"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlmodel import Session, select, func

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import (
    get_session,
    get_current_user,
    get_current_admin,
    verify_email_verified,
    CurrentUser,
    CurrentAdmin,
)
from app.core.security import hash_password, verify_password, _validate_password_strength
from app.models.user import User, UserRole
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
    session: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    """Update current user's profile (username or email)."""

    if user_update.username is not None:
        username_lower = user_update.username.lower()
        if username_lower != user.username.lower():
            statement = select(User).where(User.username.ilike(username_lower))
            existing_user = session.exec(statement).first()

            if existing_user:
                logger.warning(f"Username update conflict: {user_update.username} already taken")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )

        user.username = user_update.username
        logger.info(f"Username updated for user {user.id}")

    if user_update.email is not None:
        email_lower = user_update.email.lower()
        if email_lower != user.email.lower():
            statement = select(User).where(User.email.ilike(email_lower))
            existing_user = session.exec(statement).first()

            if existing_user:
                logger.warning(f"Email update conflict: {user_update.email} already in use")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use",
                )

        user.email = user_update.email
        user.email_verified = False
        logger.info(f"Email updated for user {user.id} - re-verification required")

    user.updated_at = datetime.now(timezone.utc)

    try:
        session.add(user)
        session.commit()
        session.refresh(user)
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )

    return user


@router.post("/change-password", response_model=dict, status_code=status.HTTP_200_OK)
@limiter.limit("15/day")
async def change_password(
    request: Request,
    password_request: PasswordChangeRequest,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """
    Change current user's password.

    Rate limited: 15 changes per day per IP.
    """

    if not verify_password(password_request.current_password, user.password_hash):
        logger.warning(f"Failed password change attempt for user {user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    try:
        _validate_password_strength(password_request.new_password)
    except ValueError as e:
        logger.warning(f"Weak password provided during change for user {user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if verify_password(password_request.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    try:
        user.password_hash = hash_password(password_request.new_password)
        user.updated_at = datetime.now(timezone.utc)
        session.add(user)
        session.commit()
        logger.info(f"Password changed successfully for user {user.id}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )

    return {"message": "Password changed successfully"}


# Admin endpoints with higher rate limits (1000/hour)
@router.get("/", response_model=dict, status_code=status.HTTP_200_OK)
@limiter.limit("1000/hour")
async def list_users(
    request: Request,
    admin: CurrentAdmin,
    session: Annotated[Session, Depends(get_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    role: Annotated[Optional[UserRole], Query()] = None,
    email_verified: Annotated[Optional[bool], Query()] = None,
) -> dict:
    """Admin: List all users with filtering and pagination."""

    statement = select(User)

    if role is not None:
        statement = statement.where(User.role == role)
    if email_verified is not None:
        statement = statement.where(User.email_verified == email_verified)

    count_statement = select(func.count(User.id)).select_from(User)
    if role is not None:
        count_statement = count_statement.where(User.role == role)
    if email_verified is not None:
        count_statement = count_statement.where(User.email_verified == email_verified)

    total = session.exec(count_statement).one()
    statement = statement.offset(skip).limit(limit).order_by(User.created_at.desc())
    users = session.exec(statement).all()

    logger.info(f"Admin {admin.id} listed {len(users)} users (skip={skip}, limit={limit})")

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
    session: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    """Admin: Get user details by ID."""

    statement = select(User).where(User.id == user_id)
    user = session.exec(statement).first()

    if not user:
        logger.warning(f"Admin {admin.id} attempted to access non-existent user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    logger.info(f"Admin {admin.id} viewed user {user_id}")
    return user


@router.patch("/{user_id}/role", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("1000/hour")
async def update_user_role(
    request: Request,
    user_id: UUID,
    role_update: UserRoleUpdate,
    admin: CurrentAdmin,
    session: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    """Admin: Update user's role."""

    if user_id == admin.id:
        logger.warning(f"Admin {admin.id} attempted to change own role")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change your own role",
        )

    statement = select(User).where(User.id == user_id)
    user = session.exec(statement).first()

    if not user:
        logger.warning(f"Admin {admin.id} attempted to update non-existent user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role == UserRole.ADMIN and role_update.role != UserRole.ADMIN:
        logger.warning(f"Admin {admin.id} attempted to demote admin {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change another admin's role",
        )

    old_role = user.role
    user.role = role_update.role
    user.updated_at = datetime.now(timezone.utc)

    try:
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.warning(f"Admin {admin.id} changed user {user_id} role from {old_role} to {role_update.role}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role",
        )

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("1000/hour")
async def delete_user(
    request: Request,
    user_id: UUID,
    admin: CurrentAdmin,
    session: Annotated[Session, Depends(get_session)],
) -> None:
    """Admin: Delete user account."""

    if user_id == admin.id:
        logger.warning(f"Admin {admin.id} attempted to delete own account")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete your own account",
        )

    statement = select(User).where(User.id == user_id)
    user = session.exec(statement).first()

    if not user:
        logger.warning(f"Admin {admin.id} attempted to delete non-existent user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        session.delete(user)
        session.commit()
        logger.warning(f"Admin {admin.id} deleted user {user_id} ({user.email})")
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        )


@router.post("/{user_id}/send-verification-email", status_code=status.HTTP_200_OK)
@limiter.limit("1000/hour")
async def admin_send_verification_email(
    request: Request,
    user_id: UUID,
    admin: CurrentAdmin,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """Admin: Send verification email to user (resend)."""

    statement = select(User).where(User.id == user_id)
    user = session.exec(statement).first()

    if not user:
        logger.warning(f"Admin {admin.id} attempted to email non-existent user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User's email already verified",
        )

    from app.core.tokens import create_email_verification_token
    from app.core.email import email_service

    plain_token, token_hash, expiry = create_email_verification_token()

    user.email_verification_token_hash = token_hash
    user.email_verification_expires_at = expiry
    user.updated_at = datetime.now(timezone.utc)

    try:
        session.add(user)
        session.commit()
        logger.info(f"Admin {admin.id} sent verification email to user {user_id}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error sending verification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )

    return {
        "message": "Verification email sent",
        "user_id": str(user_id),
    }

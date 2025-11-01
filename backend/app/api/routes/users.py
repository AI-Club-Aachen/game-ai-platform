from typing import Annotated
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.api.deps import get_session, get_current_user, get_current_admin
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    UserRoleUpdate,
    PasswordReset
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
        current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current authenticated user profile"""
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_current_user_profile(
        user_update: UserUpdate,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)]
) -> User:
    """Update current user profile"""

    # Check username uniqueness if being updated
    if user_update.username and user_update.username != current_user.username:
        statement = select(User).where(User.username == user_update.username)
        existing_user = session.exec(statement).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = user_update.username

    # Check email uniqueness if being updated
    if user_update.email and user_update.email != current_user.email:
        statement = select(User).where(User.email == user_update.email)
        existing_user = session.exec(statement).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already taken"
            )
        current_user.email = user_update.email

    # Update password if provided
    if user_update.password:
        current_user.password_hash = get_password_hash(user_update.password)

    current_user.updated_at = datetime.now(timezone.utc)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return current_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
        user_id: UUID,
        current_admin: Annotated[User, Depends(get_current_admin)],
        session: Annotated[Session, Depends(get_session)]
) -> User:
    """Admin: Get user by ID"""

    statement = select(User).where(User.id == user_id)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_user_role(
        user_id: UUID,
        role_update: UserRoleUpdate,
        current_admin: Annotated[User, Depends(get_current_admin)],
        session: Annotated[Session, Depends(get_session)]
) -> User:
    """Admin: Update user role"""

    statement = select(User).where(User.id == user_id)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.role = role_update.role
    user.updated_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    session.refresh(user)

    return user


@router.post("/{user_id}/reset-password", response_model=UserResponse)
def reset_user_password(
        user_id: UUID,
        password_reset: PasswordReset,
        current_admin: Annotated[User, Depends(get_current_admin)],
        session: Annotated[Session, Depends(get_session)]
) -> User:
    """Admin: Reset user password"""

    statement = select(User).where(User.id == user_id)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.password_hash = get_password_hash(password_reset.new_password)
    user.updated_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    session.refresh(user)

    return user

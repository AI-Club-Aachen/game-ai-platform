"""Authentication routes with security best practices and rate limiting"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlmodel import Session, select

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_session
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.core.tokens import (
    create_email_verification_token,
    create_password_reset_token,
    safe_verify_token_hash,
    is_token_expired,
)
from app.core.email import email_service
from app.models.user import User, UserRole
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
        session: Annotated[Session, Depends(get_session)],
) -> dict:
    """
    Register new user with email verification.

    Allows re-registration if previous account is unverified.
    Rate limited: 20 registrations per hour per IP.
    """

    # Validate password strength
    try:
        password_hash = hash_password(user_data.password)
    except ValueError as e:
        logger.warning(f"Password validation failed for registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Check username uniqueness (case-insensitive)
    username_lower = user_data.username.lower()
    statement = select(User).where(User.username.ilike(username_lower))
    existing_user = session.exec(statement).first()

    if existing_user:
        if existing_user.email_verified:
            logger.warning(f"Registration attempt with verified username: {user_data.username}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered",
            )
        else:
            # Delete unverified account to allow re-registration
            logger.info(f"Deleting unverified account for re-registration: {existing_user.id}")
            session.delete(existing_user)
            session.flush()  # Ensure deletion is processed before proceeding

    # Check email uniqueness (case-insensitive)
    email_lower = user_data.email.lower()
    statement = select(User).where(User.email.ilike(email_lower))
    existing_user = session.exec(statement).first()

    if existing_user:
        if existing_user.email_verified:
            logger.warning(f"Registration attempt with verified email: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        else:
            # Delete unverified account to allow re-registration
            logger.info(f"Deleting unverified account for re-registration: {existing_user.id}")
            session.delete(existing_user)
            session.flush()  # Ensure deletion is processed before proceeding

    # Generate verification token
    plain_token, token_hash, expiry = create_email_verification_token()

    # Create user
    now = datetime.now(timezone.utc)
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
        role=UserRole.GUEST,
        email_verified=False,
        email_verification_token_hash=token_hash,
        email_verification_expires_at=expiry,
        created_at=now,
        updated_at=now,
    )

    try:
        session.add(user)
        session.commit()
        session.refresh(user)
    except Exception as e:
        session.rollback()
        logger.error(f"Database error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account",
        )

    # Send verification email in background
    background_tasks.add_task(
        email_service.send_verification_email,
        to_email=user.email,
        username=user.username,
        token=plain_token,
    )

    logger.info(f"New user registered: {user.email} (ID: {user.id})")
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
    session: Annotated[Session, Depends(get_session)],
) -> LoginResponse:
    """
    Login with email and password.

    Rate limited: 30 per minute, 200 per day per IP.
    """

    # Query user by email (case-insensitive)
    email_lower = login_request.email.lower()
    statement = select(User).where(User.email.ilike(email_lower))
    user = session.exec(statement).first()

    # Verify password
    if not user or not verify_password(login_request.password, user.password_hash):
        logger.warning(f"Failed login attempt: {login_request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check email verification status
    if not user.email_verified:
        logger.warning(f"Login attempt with unverified email: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Check your inbox for verification link.",
        )

    # Create access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
        },
        expires_delta=timedelta(hours=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS),
    )

    logger.info(f"User logged in: {user.email} (ID: {user.id})")
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=str(user.id),
        username=user.username,
    )


@router.post("/verify-email", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    token: str,
    session: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    """Verify email address with token sent via email."""

    # Query unverified users with verification tokens
    statement = select(User).where(
        User.email_verified == False,
        User.email_verification_token_hash.isnot(None),
    )

    users = session.exec(statement).all()

    # Find matching token (constant-time comparison)
    matched_user = None
    for u in users:
        if safe_verify_token_hash(token, u.email_verification_token_hash):
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
        logger.warning(f"Expired verification token used: {matched_user.email}")
        matched_user.email_verification_token_hash = None
        matched_user.email_verification_expires_at = None
        matched_user.updated_at = datetime.now(timezone.utc)
        session.add(matched_user)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token expired. Request a new one.",
        )

    # Mark email as verified
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

    logger.info(f"Email verified: {matched_user.email} (ID: {matched_user.id})")
    return matched_user


@router.post("/request-password-reset", status_code=status.HTTP_200_OK)
@limiter.limit("10/hour")
async def request_password_reset(
    request: Request,
    email: str,
    background_tasks: BackgroundTasks,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    """
    Request password reset via email.

    Rate limited: 10 per hour per IP.
    """

    email_lower = email.lower()
    statement = select(User).where(User.email.ilike(email_lower))
    user = session.exec(statement).first()

    # Always return same message (prevent email enumeration)
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
            logger.error(f"Error processing password reset: {e}")

    return {"message": "If email exists, password reset link will be sent"}


@router.post("/reset-password", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    token: str,
    new_password: str,
    session: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    """Reset password with token sent via email."""

    # Validate new password
    try:
        from app.core.security import _validate_password_strength
        _validate_password_strength(new_password)
        password_hash = hash_password(new_password)
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

    # Find matching token
    matched_user = None
    for u in users:
        if safe_verify_token_hash(token, u.password_reset_token_hash):
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
        logger.warning(f"Expired reset token used: {matched_user.email}")
        matched_user.password_reset_token_hash = None
        matched_user.password_reset_expires_at = None
        matched_user.updated_at = datetime.now(timezone.utc)
        session.add(matched_user)
        session.commit()
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

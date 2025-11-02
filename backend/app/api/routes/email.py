"""Email verification and password reset routes"""

from typing import Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.api.deps import get_session, get_current_user
from app.core.email import email_service
from app.core.tokens import (
    generate_secure_token,
    hash_token,
    verify_token_hash,
    get_token_expiry,
    is_token_expired,
)
from app.core.config import settings
from app.models.user import User
from app.schemas.email import (
    EmailVerificationRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/email", tags=["Email"])


@router.post("/send-verification")
async def send_verification_email(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, str]:
    """Send email verification link to current user"""

    # Generate verification token
    token = generate_secure_token()
    token_hash = hash_token(token)
    expires_at = get_token_expiry(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)

    # Store token hash in database
    current_user.email_verification_token_hash = token_hash
    current_user.email_verification_expires_at = expires_at
    session.add(current_user)
    session.commit()

    # Build verification URL (frontend will handle this)
    verification_url = f"https://your-frontend-domain.com/verify-email?token={token}"

    # Email content
    html_content = f"""
    <html>
      <body>
        <h1>Email Verification</h1>
        <p>Hello {current_user.username},</p>
        <p>Please verify your email by clicking the link below:</p>
        <p><a href="{verification_url}">Verify Email</a></p>
        <p>This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.</p>
        <p>If you did not request this, please ignore this email.</p>
      </body>
    </html>
    """

    # Send email
    success = await email_service.send_email(
        to_email=current_user.email,
        subject="Verify Your Email - AI Game Competition Platform",
        html_content=html_content,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again.",
        )

    return {"message": "Verification email sent. Check your inbox."}


@router.post("/verify", response_model=UserResponse)
async def verify_email(
    request: EmailVerificationRequest,
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """Verify email with token"""

    # Find user with matching token hash
    statement = select(User).where(
        User.email_verification_token_hash.isnot(None)
    )
    users = session.exec(statement).all()

    user = None
    for u in users:
        if u.email_verification_token_hash and verify_token_hash(
            request.token, u.email_verification_token_hash
        ):
            user = u
            break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    # Check if token expired
    if is_token_expired(user.email_verification_expires_at):
        user.email_verification_token_hash = None
        user.email_verification_expires_at = None
        session.add(user)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token expired. Request a new one.",
        )

    # Mark email as verified
    user.email_verified = True
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    user.updated_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    session.refresh(user)

    return user


@router.post("/request-password-reset")
async def request_password_reset(
    request: PasswordResetRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, str]:
    """Request password reset email"""

    # Find user by email
    statement = select(User).where(User.email == request.email)
    user = session.exec(statement).first()

    if not user:
        # Don't reveal if email exists (security best practice)
        return {"message": "If email exists, password reset link will be sent."}

    # Generate reset token
    token = generate_secure_token()
    token_hash = hash_token(token)
    expires_at = get_token_expiry(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )

    # Store token hash in database
    user.password_reset_token_hash = token_hash
    user.password_reset_expires_at = expires_at
    session.add(user)
    session.commit()

    # Build reset URL (frontend will handle this)
    reset_url = f"https://your-frontend-domain.com/reset-password?token={token}"

    # Email content
    html_content = f"""
    <html>
      <body>
        <h1>Password Reset</h1>
        <p>Hello {user.username},</p>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_url}">Reset Password</a></p>
        <p>This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
        <p>If you did not request this, please ignore this email.</p>
      </body>
    </html>
    """

    # Send email (don't fail if send fails - user can request again)
    await email_service.send_email(
        to_email=user.email,
        subject="Reset Your Password - AI Game Competition Platform",
        html_content=html_content,
    )

    return {"message": "If email exists, password reset link will be sent."}


@router.post("/reset-password", response_model=UserResponse)
async def reset_password(
    request: PasswordResetConfirm,
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """Reset password with token"""

    from app.core.security import get_password_hash

    # Find user with matching token hash
    statement = select(User).where(
        User.password_reset_token_hash.isnot(None)
    )
    users = session.exec(statement).all()

    user = None
    for u in users:
        if u.password_reset_token_hash and verify_token_hash(
            request.token, u.password_reset_token_hash
        ):
            user = u
            break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token",
        )

    # Check if token expired
    if is_token_expired(user.password_reset_expires_at):
        user.password_reset_token_hash = None
        user.password_reset_expires_at = None
        session.add(user)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token expired. Request a new one.",
        )

    # Update password
    user.password_hash = get_password_hash(request.new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    user.updated_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    session.refresh(user)

    return user

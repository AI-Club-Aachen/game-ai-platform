"""Email-related request/response schemas"""

from pydantic import BaseModel, EmailStr, Field


class EmailVerificationRequest(BaseModel):
    """Request to verify email with token"""
    token: str = Field(..., min_length=16, max_length=512)


class PasswordResetRequest(BaseModel):
    """Request to initiate password reset"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Request to complete password reset with token"""
    token: str = Field(..., min_length=16, max_length=512)
    new_password: str = Field(..., min_length=12, max_length=128)


class ResendVerificationEmailRequest(BaseModel):
    """Request to resend verification email"""
    pass  # No additional data needed - uses authenticated user

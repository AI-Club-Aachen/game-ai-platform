"""Email-related schemas"""

from pydantic import BaseModel, EmailStr


class EmailVerificationRequest(BaseModel):
    """Request to verify email with token"""
    token: str


class PasswordResetRequest(BaseModel):
    """Request to initiate password reset"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Request to complete password reset with token"""
    token: str
    new_password: str

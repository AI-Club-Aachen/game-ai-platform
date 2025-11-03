from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Schema for login response"""
    access_token: str
    token_type: str
    user_id: str
    username: str


class TokenData(BaseModel):
    """Schema for JWT token payload"""
    sub: Optional[str] = None
    role: Optional[str] = None


class PasswordReset(BaseModel):
    """Schema for password reset request"""
    email: EmailStr = Field(..., description="User email address")
    reset_token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class PasswordResetRequest(BaseModel):
    """Schema for initiating password reset"""
    email: EmailStr = Field(..., description="User email address")
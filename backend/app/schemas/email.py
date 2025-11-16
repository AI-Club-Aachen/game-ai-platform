"""Email-related request/response schemas"""

from pydantic import BaseModel, EmailStr, Field


class EmailVerificationRequest(BaseModel):
    """Request to verify email with token"""
    token: str = Field(..., min_length=16, max_length=512)
"""Email-related request/response schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EmailVerificationRequest(BaseModel):
    """Request to verify email with token"""

    token: str = Field(..., min_length=16, max_length=512)


class EmailVerificationResponse(BaseModel):
    """Response after triggering email verification"""

    message: str


class AdminEmailVerificationResponse(EmailVerificationResponse):
    """Response for admin triggering email verification"""

    user_id: str


class VerificationStatusResponse(BaseModel):
    """Response for checking email verification status"""

    email: str
    email_verified: bool
    verification_expires_at: datetime | None
    can_resend: bool

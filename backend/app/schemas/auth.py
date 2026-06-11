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
    role: str


class RegistrationResponse(BaseModel):
    """Response for user registration"""

    message: str
    user_id: str
    email: EmailStr


class PasswordResetRequest(BaseModel):
    """Request a password-reset email."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirm a password reset."""

    token: str = Field(..., min_length=16, max_length=512)
    new_password: str = Field(..., min_length=12, max_length=128)


class PasswordResetRequestResponse(BaseModel):
    """Response for password reset request"""

    message: str

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


class PasswordResetRequestResponse(BaseModel):
    """Response for password reset request"""

    message: str

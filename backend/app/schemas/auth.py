from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for JWT token payload data"""
    user_id: Optional[str] = None

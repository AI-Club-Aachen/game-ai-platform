"""Schemas package - centralized imports for all request/response schemas"""

# Authentication schemas
from app.schemas.auth import LoginRequest, LoginResponse

# Email schemas
from app.schemas.email import EmailVerificationRequest

# User schemas
from app.schemas.user import (
    PasswordChangeRequest,
    UserCreate,
    UserResponse,
    UserRoleUpdate,
    UserUpdate,
)


__all__ = [
    "EmailVerificationRequest",
    "LoginRequest",
    "LoginResponse",
    "PasswordChangeRequest",
    "UserCreate",
    "UserResponse",
    "UserRoleUpdate",
    "UserUpdate",
]

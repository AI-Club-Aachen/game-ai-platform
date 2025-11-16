"""Schemas package - centralized imports for all request/response schemas"""

# Authentication schemas
from app.schemas.auth import (
    LoginRequest,
    LoginResponse
)

# User schemas
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserRoleUpdate,
    PasswordChangeRequest,
)

# Email schemas
from app.schemas.email import (
    EmailVerificationRequest
)

__all__ = [
    # Auth
    "LoginRequest",
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserRoleUpdate",
    "PasswordChangeRequest",
    # Email
    "EmailVerificationRequest"
]

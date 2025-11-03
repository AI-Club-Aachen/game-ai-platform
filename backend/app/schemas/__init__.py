"""Schemas package - centralized imports for all request/response schemas"""

# Authentication schemas
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    TokenData,
    PasswordReset,
    PasswordResetRequest as AuthPasswordResetRequest,
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
    EmailVerificationRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    ResendVerificationEmailRequest,
)

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "TokenData",
    "PasswordReset",
    "AuthPasswordResetRequest",
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserRoleUpdate",
    "PasswordChangeRequest",
    # Email
    "EmailVerificationRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "ResendVerificationEmailRequest",
]

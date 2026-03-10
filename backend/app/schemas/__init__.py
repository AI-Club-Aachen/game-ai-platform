"""Schemas package - centralized imports for all request/response schemas"""

# Authentication schemas
from app.schemas.auth import LoginRequest, LoginResponse

# Email schemas
from app.schemas.email import EmailVerificationRequest

# Match schemas
from app.schemas.match import GameInfo, MatchCreate, MatchRead, MatchUpdate

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
    "GameInfo",
    "LoginRequest",
    "LoginResponse",
    "MatchCreate",
    "MatchRead",
    "MatchUpdate",
    "PasswordChangeRequest",
    "UserCreate",
    "UserResponse",
    "UserRoleUpdate",
    "UserUpdate",
]

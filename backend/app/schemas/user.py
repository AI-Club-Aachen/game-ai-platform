from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


# URL constrained like username: http(s) only, safe length.
MAX_PROFILE_PICTURE_URL_LENGTH = 2048


def _validate_profile_picture_url(v: str | None) -> str | None:
    if v is None:
        return v
    if len(v) > MAX_PROFILE_PICTURE_URL_LENGTH:
        raise ValueError(f"profile_picture_url must not exceed {MAX_PROFILE_PICTURE_URL_LENGTH} characters")
    if not v.startswith(("https://", "http://")):
        raise ValueError("profile_picture_url must be an http:// or https:// URL")
    return v


class UserCreate(BaseModel):
    """Schema for user registration"""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    profile_picture_url: str | None = None

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """Validate username format"""
        if not all(c.isalnum() or c in "_-" for c in v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v

    @field_validator("profile_picture_url")
    @classmethod
    def validate_profile_picture_url(cls, v: str | None) -> str | None:
        return _validate_profile_picture_url(v)


class UserUpdate(BaseModel):
    """Schema for updating user profile"""

    username: str | None = Field(None, min_length=3, max_length=50)
    email: EmailStr | None = None
    profile_picture_url: str | None = None

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str | None) -> str | None:
        if v is not None and not all(c.isalnum() or c in "_-" for c in v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v

    @field_validator("profile_picture_url")
    @classmethod
    def validate_profile_picture_url(cls, v: str | None) -> str | None:
        return _validate_profile_picture_url(v)


class PasswordChangeRequest(BaseModel):
    """Schema for changing password"""

    current_password: str
    new_password: str = Field(..., min_length=12, max_length=128)


class UserResponse(BaseModel):
    """Schema for user response"""

    id: UUID
    username: str
    email: EmailStr
    role: UserRole
    profile_picture_url: str | None
    email_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminUserStats(BaseModel):
    """Admin-only aggregate usage stats for a user."""

    agents_count: int = 0
    submissions_count: int = 0
    matches_played_total: int = 0
    running_containers_count: int = 0
    failed_containers_count: int = 0
    latest_submission_at: datetime | None = None


class AdminUserListItem(UserResponse):
    """User list item enriched with admin-only usage stats."""

    stats: AdminUserStats


class UserRoleUpdate(BaseModel):
    """Schema for admin updating user role"""

    role: UserRole


class ChangePasswordResponse(BaseModel):
    """Response for password change"""

    message: str


class UserListResponse(BaseModel):
    """Response for listing users with pagination"""

    data: list[AdminUserListItem]
    total: int
    skip: int
    limit: int


class UserRoleList(BaseModel):
    """Response schema for available user roles"""

    roles: list[UserRole]

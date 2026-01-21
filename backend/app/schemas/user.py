from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


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
            raise ValueError("Username must be alphanumeric (with _ or - allowed)")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user profile"""

    username: str | None = Field(None, min_length=3, max_length=50)
    email: EmailStr | None = None
    profile_picture_url: str | None = None

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str | None) -> str | None:
        if v is not None and not all(c.isalnum() or c in "_-" for c in v):
            raise ValueError("Username must be alphanumeric (with _ or - allowed)")
        return v


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


class UserRoleUpdate(BaseModel):
    """Schema for admin updating user role"""

    role: UserRole


class ChangePasswordResponse(BaseModel):
    """Response for password change"""

    message: str


class UserListResponse(BaseModel):
    """Response for listing users with pagination"""

    data: list[UserResponse]
    total: int
    skip: int
    limit: int


class UserRoleList(BaseModel):
    """Response schema for available user roles"""

    roles: list[UserRole]

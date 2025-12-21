from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Column, Field, Index, SQLModel, String


class UserRole(str, Enum):
    """User role enumeration"""

    GUEST = "guest"
    USER = "user"
    ADMIN = "admin"


class User(SQLModel, table=True):
    """User database model with email verification and password reset tokens"""

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    username: str = Field(sa_column=Column(String, unique=True, index=True, nullable=False))
    email: str = Field(sa_column=Column(String, unique=True, index=True, nullable=False))
    password_hash: str = Field(nullable=False)
    role: UserRole = Field(default=UserRole.GUEST, nullable=False)
    profile_picture_url: str | None = Field(default=None, nullable=True)

    # Email verification fields
    email_verified: bool = Field(default=False, nullable=False, index=True)
    email_verification_token_hash: str | None = Field(default=None, nullable=True, index=True)
    email_verification_expires_at: datetime | None = Field(default=None, nullable=True)

    # Password reset fields
    password_reset_token_hash: str | None = Field(default=None, nullable=True, index=True)
    password_reset_expires_at: datetime | None = Field(default=None, nullable=True)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    # Add composite index for cleanup queries
    __table_args__ = (
        Index("ix_email_verification_expires_at", "email_verification_expires_at"),
        Index("ix_password_reset_expires_at", "password_reset_expires_at"),
    )

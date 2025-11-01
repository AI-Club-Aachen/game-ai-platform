from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4
from enum import Enum
from sqlmodel import Field, SQLModel, Column, String


class UserRole(str, Enum):
    """User role enumeration"""
    GUEST = "guest"
    USER = "user"
    ADMIN = "admin"


class User(SQLModel, table=True):
    """User database model"""

    __tablename__ = "users"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    username: str = Field(
        sa_column=Column(String, unique=True, index=True, nullable=False)
    )
    email: str = Field(
        sa_column=Column(String, unique=True, index=True, nullable=False)
    )
    password_hash: str = Field(nullable=False)
    role: UserRole = Field(
        default=UserRole.GUEST,
        nullable=False
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )

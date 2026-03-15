from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field, SQLModel


class Agent(SQLModel, table=True):
    """
    Represents an agent of a user that can participate in a match.
    """

    __tablename__ = "agents"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)

    user_id: UUID = Field(index=True, nullable=False)

    active_submission_id: UUID = Field(nullable=True)

    stats: dict[str, Any] = Field(default={}, sa_column=Column(JSON))  # TODO: change from freeform json

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

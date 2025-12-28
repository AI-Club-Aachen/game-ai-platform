from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field, SQLModel


class MatchStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Match(SQLModel, table=True):
    """
    Represents a game match between agents.
    """

    __tablename__ = "matches"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)

    status: MatchStatus = Field(default=MatchStatus.QUEUED, nullable=False)

    # Configuration for the match (e.g. which agents, game rules, seed)
    config: dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Result of the match (e.g. scores, winner, replay data)
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    # Logs from the match execution
    logs: str | None = Field(default=None, nullable=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

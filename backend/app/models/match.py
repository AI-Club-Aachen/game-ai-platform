from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field, SQLModel

from app.models.game import GameType


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

    # Reference to the game type being played
    game_type: GameType = Field(nullable=False, index=True)

    status: MatchStatus = Field(default=MatchStatus.QUEUED, nullable=False)

    # Agents that participate in the match
    agent_ids: list[UUID] = Field(default=[], sa_column=Column(JSON))

    # Configuration for the match (e.g. which agents, game rules, seed)
    config: dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Result of the match (e.g. scores, winner, replay data)
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    # Logs from the match execution
    logs: str | None = Field(default=None, nullable=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

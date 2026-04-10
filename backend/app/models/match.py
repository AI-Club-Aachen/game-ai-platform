from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlmodel import JSON, Column, Field, SQLModel

from app.models.game import GameType


class MatchStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CLIENT_ERROR = "client_error"


class MatchResultReason(str, Enum):
    """Known reasons a match can end — used in match.result['reason']."""

    GAME_FINISHED = "Game finished"
    DRAW = "Draw"
    TURN_LIMIT_REACHED = "Turn limit reached"
    TIME_LIMIT_EXCEEDED = "Time limit exceeded"
    INVALID_MOVE = "Invalid move"
    COMMUNICATION_ERROR = "Communication error"


class MatchConfig(BaseModel):
    """
    Typed configuration for a match.

    Serialised as JSON in the ``config`` column; extend this model to add
    new per-match settings without touching the DB schema.
    """

    # Maximum seconds an agent may take per turn (None = no enforced limit).
    turn_time_limit: float | None = 10.0


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

    # The current state of the game
    game_state: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

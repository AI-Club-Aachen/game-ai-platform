from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from app.models.game import GameType


if TYPE_CHECKING:
    from app.models.arena import Arena


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

    turn_time_limit: float = 5.0
    state_init_data: dict[str, Any] = {}


class Match(SQLModel, table=True):
    """
    Represents a game match between agents.
    """

    __tablename__ = "matches"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)

    # Reference to the game type being played
    game_type: GameType = Field(nullable=False, index=True)

    arena_id: UUID = Field(foreign_key="arenas.id", nullable=False, index=True)
    arena: Optional["Arena"] = Relationship(back_populates="matches")

    status: MatchStatus = Field(default=MatchStatus.QUEUED, nullable=False)

    # Agents that participate in the match
    agent_ids: list[UUID] = Field(default=[], sa_column=Column(JSON))

    # Set for matches played as part of a tournament; such matches are excluded
    # from global agent stats and from the random auto-scheduler.
    tournament_id: UUID | None = Field(default=None, foreign_key="tournaments.id", nullable=True, index=True)

    # Configuration for the match (e.g. which agents, game rules, seed)
    config: dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Result of the match (e.g. scores, winner, replay data)
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    # The current state of the game
    game_state: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    # Logs from the match execution
    logs: str = Field(default="")

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

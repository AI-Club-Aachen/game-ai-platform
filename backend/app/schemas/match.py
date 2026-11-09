from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.game import GameType
from app.models.match import MatchConfig, MatchStatus


class MatchBase(BaseModel):
    game_type: GameType | None = None
    arena_id: UUID
    config: MatchConfig = MatchConfig()
    agent_ids: list[UUID] = []


class MatchCreate(MatchBase):
    pass


class HumanMatchCreate(BaseModel):
    arena_id: UUID
    agent_id: UUID
    human_player_index: int = Field(default=0, ge=0, le=1)  # 0 moves first


class HumanMoveSubmit(BaseModel):
    move: dict[str, Any]  # "player" is set server-side


class MatchUpdate(BaseModel):
    """Schema for updating a match (used by workers)."""

    status: MatchStatus
    logs: str | None = None
    result: dict[str, Any] | None = None
    game_state: dict[str, Any] | None = None
    # Seconds the human has for the move the runner now waits on.
    human_turn_seconds: float | None = Field(default=None, ge=0, le=3600)


class MatchRead(MatchBase):
    id: UUID
    status: MatchStatus
    agent_ids: list[UUID]
    logs: str
    result: dict[str, Any] | None
    game_state: dict[str, Any] | None
    human_user_id: UUID | None = None
    human_player_index: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("config", mode="before")
    @classmethod
    def coerce_config(cls, v: Any) -> MatchConfig:
        """Accept a raw dict from the DB and coerce it into a MatchConfig."""
        if isinstance(v, dict):
            return MatchConfig(**v)
        return v


class PlayableAgentRead(BaseModel):
    id: UUID
    agent_name: str
    username: str
    elo: int | None
    is_mine: bool


class GameInfo(BaseModel):
    """Schema for returning game information."""

    game_type: GameType
    display_name: str
    description: str
    icon: str
    min_players: int
    max_players: int
    is_turn_based: bool

    model_config = ConfigDict(from_attributes=True)

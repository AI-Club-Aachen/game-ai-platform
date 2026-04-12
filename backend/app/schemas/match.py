from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.game import GameType
from app.models.match import MatchConfig, MatchStatus


class MatchBase(BaseModel):
    game_type: GameType
    config: MatchConfig = MatchConfig()
    agent_ids: list[UUID] = []


class MatchCreate(MatchBase):
    pass


class MatchUpdate(BaseModel):
    """Schema for updating a match (used by workers)."""

    status: MatchStatus
    logs: str | None = None
    result: dict[str, Any] | None = None
    game_state: dict[str, Any] | None = None


class MatchRead(MatchBase):
    id: UUID
    status: MatchStatus
    agent_ids: list[UUID]
    logs: str
    result: dict[str, Any] | None
    game_state: dict[str, Any] | None
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

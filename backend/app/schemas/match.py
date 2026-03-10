from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.game import GameType
from app.models.match import MatchStatus


class MatchBase(BaseModel):
    game_type: GameType
    config: dict[str, Any] = {}
    agent_ids: list[UUID] = []


class MatchCreate(MatchBase):
    pass


class MatchUpdate(BaseModel):
    """Schema for updating a match (used by workers)."""
    status: MatchStatus
    result: dict[str, Any] | None = None


class MatchRead(MatchBase):
    id: UUID
    status: MatchStatus
    agent_ids: list[UUID]
    result: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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

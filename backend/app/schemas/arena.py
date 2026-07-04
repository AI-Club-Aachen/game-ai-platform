from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.game import GameType


class ArenaBase(BaseModel):
    name: str
    game_type: GameType
    description: Optional[str] = None
    config: dict[str, Any] = {}
    is_active: bool = True


class ArenaCreate(ArenaBase):
    password: Optional[str] = None


class ArenaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class ArenaRead(ArenaBase):
    id: UUID
    has_password: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

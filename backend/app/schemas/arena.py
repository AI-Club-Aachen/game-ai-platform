from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.game import GameType


class ArenaBase(BaseModel):
    name: str
    game_type: GameType
    description: str | None = None
    config: dict[str, Any] = {}
    is_active: bool = True
    packages: Literal["numpy", "torch"] = "numpy"


class ArenaCreate(ArenaBase):
    password: str | None = None


class ArenaUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    password: str | None = None
    is_active: bool | None = None
    packages: Literal["numpy", "torch"] | None = None

    model_config = ConfigDict(extra="forbid")


class ArenaRead(ArenaBase):
    id: UUID
    has_password: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

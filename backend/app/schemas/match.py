from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.match import MatchStatus


class MatchBase(BaseModel):
    config: dict[str, Any] = {}


class MatchCreate(MatchBase):
    pass


class MatchRead(MatchBase):
    id: UUID
    status: MatchStatus
    result: dict[str, Any] | None
    logs: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentBase(BaseModel):
    pass


class AgentCreate(AgentBase):
    user_id: UUID
    active_submission_id: UUID


class AgentUpdate(AgentBase):
    active_submission_id: UUID | None = None
    stats: dict[str, Any] | None = None


class AgentRead(AgentBase):
    id: UUID
    user_id: UUID
    active_submission_id: UUID
    stats: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

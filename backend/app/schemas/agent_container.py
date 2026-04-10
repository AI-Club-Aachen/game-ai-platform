from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentContainerBase(BaseModel):
    container_id: str
    match_id: UUID | None = None
    agent_id: UUID
    agent_name: str | None = None
    name: str | None = None
    status: str
    image: str
    uptime_seconds: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0


class AgentContainerCreate(AgentContainerBase):
    pass


class AgentContainerUpdate(BaseModel):
    match_id: UUID | None = None
    agent_name: str | None = None
    name: str | None = None
    status: str | None = None
    image: str | None = None
    uptime_seconds: float | None = None
    cpu_percent: float | None = None
    memory_mb: float | None = None


class AgentContainerRead(AgentContainerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class AgentContainer(SQLModel, table=True):
    """Latest known runtime snapshot for an orchestration container."""

    __tablename__ = "agent_containers"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)

    container_id: str = Field(index=True, unique=True, nullable=False)
    match_id: UUID | None = Field(default=None, foreign_key="matches.id", index=True)
    agent_id: UUID = Field(foreign_key="agents.id", index=True, nullable=False)

    agent_name: str | None = Field(default=None)
    name: str | None = Field(default=None)
    status: str = Field(nullable=False)
    image: str = Field(nullable=False)

    uptime_seconds: float = Field(default=0.0, nullable=False)
    cpu_percent: float = Field(default=0.0, nullable=False)
    memory_mb: float = Field(default=0.0, nullable=False)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

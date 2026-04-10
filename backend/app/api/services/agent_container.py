import logging
from uuid import UUID

from app.api.repositories.agent_container import AgentContainerRepository, AgentContainerRepositoryError
from app.models.agent_container import AgentContainer
from app.schemas.agent_container import AgentContainerCreate, AgentContainerUpdate


logger = logging.getLogger(__name__)


class AgentContainerServiceError(Exception):
    """Base exception for agent container service errors."""


class AgentContainerService:
    """Application service for runtime container telemetry."""

    def __init__(self, repository: AgentContainerRepository) -> None:
        self._repo = repository

    def list_containers(
        self,
        skip: int = 0,
        limit: int = 100,
        match_id: UUID | None = None,
        status: str | None = None,
        owner_user_id: UUID | None = None,
    ) -> list[AgentContainer]:
        try:
            return self._repo.list_containers(
                skip=skip,
                limit=limit,
                match_id=match_id,
                status=status,
                owner_user_id=owner_user_id,
            )
        except AgentContainerRepositoryError as e:
            logger.exception("Failed to list container snapshots")
            raise AgentContainerServiceError("Failed to list container snapshots") from e

    def upsert_container(self, payload: AgentContainerCreate) -> AgentContainer:
        try:
            return self._repo.upsert(payload)
        except AgentContainerRepositoryError as e:
            logger.exception("Failed to upsert container snapshot")
            raise AgentContainerServiceError("Failed to upsert container snapshot") from e

    def update_container(self, container_id: str, payload: AgentContainerUpdate) -> AgentContainer | None:
        try:
            return self._repo.update(container_id, payload)
        except AgentContainerRepositoryError as e:
            logger.exception("Failed to update container snapshot %s", container_id)
            raise AgentContainerServiceError("Failed to update container snapshot") from e

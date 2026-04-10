import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.models.agent import Agent
from app.models.agent_container import AgentContainer
from app.schemas.agent_container import AgentContainerCreate, AgentContainerUpdate


logger = logging.getLogger(__name__)


class AgentContainerRepositoryError(Exception):
    """Base exception for agent container repository errors."""


class AgentContainerRepository:
    """Repository for agent container runtime snapshots."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_container_id(self, container_id: str) -> AgentContainer | None:
        statement = select(AgentContainer).where(AgentContainer.container_id == container_id)
        return self._session.exec(statement).first()

    def list_containers(
        self,
        skip: int,
        limit: int,
        match_id: UUID | None = None,
        status: str | None = None,
        owner_user_id: UUID | None = None,
    ) -> list[AgentContainer]:
        statement = select(AgentContainer)

        if owner_user_id is not None:
            statement = statement.join(Agent, Agent.id == AgentContainer.agent_id)
            statement = statement.where(Agent.user_id == owner_user_id)

        if match_id is not None:
            statement = statement.where(AgentContainer.match_id == match_id)
        if status is not None:
            statement = statement.where(AgentContainer.status == status)

        statement = statement.offset(skip).limit(limit).order_by(AgentContainer.updated_at.desc())
        return list(self._session.exec(statement).all())

    def upsert(self, payload: AgentContainerCreate) -> AgentContainer:
        existing = self.get_by_container_id(payload.container_id)
        now = datetime.now(UTC)

        try:
            if existing:
                for key, value in payload.model_dump(exclude_none=True).items():
                    setattr(existing, key, value)
                existing.updated_at = now
                entity = existing
            else:
                entity = AgentContainer(**payload.model_dump(exclude_none=True))
                entity.updated_at = now

            self._session.add(entity)
            self._session.commit()
            self._session.refresh(entity)
            return entity
        except Exception as e:
            self._session.rollback()
            logger.exception("Failed to upsert agent container snapshot")
            raise AgentContainerRepositoryError("Failed to upsert agent container snapshot") from e

    def update(self, container_id: str, payload: AgentContainerUpdate) -> AgentContainer | None:
        entity = self.get_by_container_id(container_id)
        if entity is None:
            return None

        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)
        entity.updated_at = datetime.now(UTC)

        try:
            self._session.add(entity)
            self._session.commit()
            self._session.refresh(entity)
            return entity
        except Exception as e:
            self._session.rollback()
            logger.exception("Failed to update agent container snapshot")
            raise AgentContainerRepositoryError("Failed to update agent container snapshot") from e

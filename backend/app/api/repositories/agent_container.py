import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func
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

    @staticmethod
    def _apply_filters(
        statement: Any,
        match_id: UUID | None,
        status: str | None,
        owner_user_id: UUID | None,
    ) -> Any:
        """Apply the shared owner/match/status filters used by list, count and tallies."""
        if owner_user_id is not None:
            statement = statement.join(Agent, Agent.id == AgentContainer.agent_id)
            statement = statement.where(Agent.user_id == owner_user_id)
        if match_id is not None:
            statement = statement.where(AgentContainer.match_id == match_id)
        if status is not None:
            statement = statement.where(AgentContainer.status == status)
        return statement

    def count_containers(
        self,
        match_id: UUID | None = None,
        status: str | None = None,
        owner_user_id: UUID | None = None,
    ) -> int:
        """Total number of containers matching the filters (ignores pagination)."""
        statement = self._apply_filters(
            select(func.count()).select_from(AgentContainer), match_id, status, owner_user_id
        )
        return self._session.exec(statement).one()

    def status_counts(
        self,
        match_id: UUID | None = None,
        status: str | None = None,
        owner_user_id: UUID | None = None,
    ) -> dict[str, int]:
        """Per-status row counts across the whole filtered set (ignores pagination)."""
        statement = self._apply_filters(
            select(AgentContainer.status, func.count()).select_from(AgentContainer),
            match_id,
            status,
            owner_user_id,
        ).group_by(AgentContainer.status)
        return {row[0]: row[1] for row in self._session.exec(statement).all()}

    def list_containers(
        self,
        skip: int,
        limit: int,
        match_id: UUID | None = None,
        status: str | None = None,
        owner_user_id: UUID | None = None,
    ) -> list[AgentContainer]:
        statement = self._apply_filters(select(AgentContainer), match_id, status, owner_user_id)
        statement = statement.offset(skip).limit(limit).order_by(AgentContainer.updated_at.desc())
        containers = list(self._session.exec(statement).all())

        if not containers:
            return containers

        agent_ids = {container.agent_id for container in containers}
        agents = self._session.exec(select(Agent).where(Agent.id.in_(agent_ids))).all()  # type: ignore[attr-defined]
        agent_names_by_id = {agent.id: agent.name for agent in agents}

        for container in containers:
            agent_name = agent_names_by_id.get(container.agent_id)
            if agent_name:
                container.agent_name = agent_name

        return containers

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
            return entity  # noqa: TRY300
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
            return entity  # noqa: TRY300
        except Exception as e:
            self._session.rollback()
            logger.exception("Failed to update agent container snapshot")
            raise AgentContainerRepositoryError("Failed to update agent container snapshot") from e

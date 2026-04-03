import logging
from uuid import UUID

from sqlmodel import Session, func, select

from app.models.agent import Agent


logger = logging.getLogger(__name__)


class AgentRepositoryError(Exception):
    """Base exception for agent repository errors."""


class AgentRepository:
    """Repository for Agent aggregate."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Queries ---

    def get_by_id(self, agent_id: UUID) -> Agent | None:
        statement = select(Agent).where(Agent.id == agent_id)
        return self._session.exec(statement).first()

    def get_by_user_id(self, user_id: UUID) -> list[Agent]:
        statement = select(Agent).where(Agent.user_id == user_id)
        return list(self._session.exec(statement).all())

    def list_agents(
        self,
        skip: int,
        limit: int,
        user_id: UUID | None = None,
    ) -> tuple[list[Agent], int]:
        """List agents with optional filters and pagination."""
        statement = select(Agent)
        count_statement = select(func.count()).select_from(Agent)

        if user_id is not None:
            statement = statement.where(Agent.user_id == user_id)
            count_statement = count_statement.where(Agent.user_id == user_id)

        total: int = self._session.exec(count_statement).one()
        statement = statement.offset(skip).limit(limit).order_by(Agent.created_at.desc())
        agents: list[Agent] = list(self._session.exec(statement).all())

        return agents, total

    # --- Commands ---

    def save(self, agent: Agent) -> Agent:
        """Persist agent, handling commit/rollback."""
        try:
            self._session.add(agent)
            self._session.commit()
            self._session.refresh(agent)
        except Exception as e:
            self._session.rollback()
            logger.exception("Error saving agent %s", getattr(agent, "id", None))
            raise AgentRepositoryError("Failed to persist agent") from e
        else:
            return agent

    def delete(self, agent: Agent) -> None:
        """Delete agent, handling commit/rollback."""
        try:
            self._session.delete(agent)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            logger.exception("Error deleting agent %s", getattr(agent, "id", None))
            raise AgentRepositoryError("Failed to delete agent") from e

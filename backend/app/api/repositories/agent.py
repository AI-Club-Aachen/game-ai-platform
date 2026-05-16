import logging
from uuid import UUID

from sqlmodel import Session, func, select

from app.models.agent import Agent
from app.models.user import User


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

    def list_by_ids(self, agent_ids: list[UUID]) -> list[Agent]:
        if not agent_ids:
            return []
        statement = select(Agent).where(Agent.id.in_(agent_ids))
        return list(self._session.exec(statement).all())

    def list_by_active_submission_id(self, submission_id: UUID) -> list[Agent]:
        statement = select(Agent).where(Agent.active_submission_id == submission_id)
        return list(self._session.exec(statement).all())

    def count_by_user_and_game(self, user_id: UUID, game_type: str) -> int:
        statement = (
            select(func.count()).select_from(Agent).where(Agent.user_id == user_id, Agent.game_type == game_type)
        )
        return self._session.exec(statement).one()

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

    def get_leaderboard(self, game_type: str, limit: int) -> list[dict]:
        statement = (
            select(Agent, User.username)
            .join(User, Agent.user_id == User.id)
            .where(Agent.game_type == game_type)
            .where(Agent.elo.is_not(None))
            .order_by(Agent.elo.desc())
            .limit(limit)
        )
        results = self._session.exec(statement).all()
        return [
            {
                "id": str(agent.id),
                "agent_name": agent.name,
                "username": username,
                "elo": agent.elo,
                "wins": agent.wins,
                "losses": agent.losses,
                "draws": agent.draws,
                "matches_played": agent.matches_played,
                "game_type": agent.game_type.value,
            }
            for agent, username in results
        ]

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

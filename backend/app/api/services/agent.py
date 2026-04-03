import logging
from datetime import UTC, datetime
from uuid import UUID

from app.api.repositories.agent import AgentRepository, AgentRepositoryError
from app.api.repositories.submission import SubmissionRepository
from app.api.services.submission_builds import submission_has_successful_build
from app.core.config import settings
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentUpdate


logger = logging.getLogger(__name__)


class AgentServiceError(Exception):
    """Base exception for agent service errors."""


class AgentNotFoundError(AgentServiceError):
    """Raised when an agent cannot be found."""


class AgentPermissionError(AgentServiceError):
    """Raised when the current user is not allowed to perform an action."""


class AgentValidationError(AgentServiceError):
    """Raised when an agent request is invalid."""


class AgentService:
    """Application service for agent-related operations."""

    def __init__(self, repository: AgentRepository, submission_repository: SubmissionRepository) -> None:
        self._repo = repository
        self._submission_repository = submission_repository

    def create_agent(self, agent_create: AgentCreate) -> Agent:
        """Create a new agent."""
        self._validate_agent_limit(agent_create.user_id, agent_create.game_type)
        if agent_create.active_submission_id is not None:
            self._validate_submission_for_agent(agent_create.active_submission_id, agent_create.user_id)

        agent = Agent(
            user_id=agent_create.user_id,
            name=agent_create.name or "",
            game_type=agent_create.game_type,
            active_submission_id=agent_create.active_submission_id,
        )
        if not agent.name.strip():
            agent.name = str(agent.id)
        try:
            return self._repo.save(agent)
        except AgentRepositoryError as e:
            logger.exception("Error creating agent")
            raise AgentServiceError("Failed to create agent") from e

    def get_agent_by_id(self, agent_id: UUID) -> Agent:
        """Get agent by id or raise."""
        agent = self._repo.get_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError("Agent not found")
        return agent

    def list_user_agents(self, user_id: UUID, skip: int = 0, limit: int = 20) -> tuple[list[Agent], int]:
        """List agents for a specific user."""
        try:
            return self._repo.list_agents(skip=skip, limit=limit, user_id=user_id)
        except AgentRepositoryError as e:
            logger.exception("Error listing agents for user %s", user_id)
            raise AgentServiceError("Failed to list agents") from e

    def update_agent(
        self,
        agent_id: UUID,
        agent_update: AgentUpdate,
        current_user_id: UUID,
        is_admin: bool = False,
    ) -> Agent:
        """Update an agent."""
        agent = self.get_agent_by_id(agent_id)

        if not is_admin and agent.user_id != current_user_id:
            raise AgentPermissionError("Not authorized to update this agent")

        if "active_submission_id" in agent_update.model_fields_set:
            if agent_update.active_submission_id is None:
                agent.active_submission_id = None
            else:
                self._validate_submission_for_agent(agent_update.active_submission_id, agent.user_id)
                agent.active_submission_id = agent_update.active_submission_id

        if agent_update.stats is not None:
            agent.stats = agent_update.stats

        agent.updated_at = datetime.now(UTC)

        try:
            return self._repo.save(agent)
        except AgentRepositoryError as e:
            logger.exception("Error updating agent %s", agent_id)
            raise AgentServiceError("Failed to update agent") from e

    def delete_agent(self, agent_id: UUID, current_user_id: UUID, is_admin: bool = False) -> None:
        """Delete an agent."""
        agent = self.get_agent_by_id(agent_id)

        if not is_admin and agent.user_id != current_user_id:
            raise AgentPermissionError("Not authorized to delete this agent")

        try:
            self._repo.delete(agent)
        except AgentRepositoryError as e:
            logger.exception("Error deleting agent %s", agent_id)
            raise AgentServiceError("Failed to delete agent") from e

    def _validate_submission_for_agent(self, submission_id: UUID, user_id: UUID) -> None:
        submission = self._submission_repository.get_by_id(submission_id)
        if not submission:
            raise AgentValidationError("Submission not found")
        if submission.user_id != user_id:
            raise AgentPermissionError("Not authorized to use this submission")
        if not submission_has_successful_build(submission):
            raise AgentValidationError("Only successfully built submissions can be attached to agents")

    def _validate_agent_limit(self, user_id: UUID, game_type: str) -> None:
        max_agents_per_game = settings.MAX_AGENTS_PER_GAME
        if max_agents_per_game <= 0:
            return

        current_count = self._repo.count_by_user_and_game(user_id, game_type)
        if current_count >= max_agents_per_game:
            raise AgentValidationError(f"Agent limit reached for game '{game_type}'")

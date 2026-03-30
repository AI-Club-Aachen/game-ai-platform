from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.api.repositories.agent import AgentRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.match import MatchRepository
from app.api.services.submission_builds import submission_has_successful_build
from app.core.queue import job_queue
from app.models.game import GameType
from app.models.job import JobStatus, MatchJob
from app.models.match import Match, MatchStatus


class MatchServiceError(Exception):
    """Base exception for match service errors."""


class MatchService:
    """Service for managing matches."""

    def __init__(
        self,
        match_repository: MatchRepository,
        job_repository: JobRepository,
        agent_repository: AgentRepository,
    ) -> None:
        self._repository = match_repository
        self._job_repository = job_repository
        self._agent_repository = agent_repository

    async def create_match(
        self,
        game_type: GameType,
        config: dict[str, Any],
        agent_ids: list[UUID],
    ) -> Match:
        """
        Create a match and queue it for execution.
        """
        self._validate_agents_for_match(game_type, agent_ids)

        match = Match(
            game_type=game_type, status=MatchStatus.QUEUED, config=config, agent_ids=[str(i) for i in agent_ids]
        )
        match = self._repository.save(match)

        # Create job
        job = MatchJob(match_id=match.id, status=JobStatus.QUEUED)
        job = self._job_repository.save_match_job(job)

        # Enqueue job
        await job_queue.enqueue_match(match.id, match.config, job.id, match.agent_ids)

        return match

    def get_match(self, match_id: str) -> Match | None:
        return self._repository.get_by_id(match_id)

    def update_match(
        self,
        match_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        game_state: dict[str, Any] | None = None,
    ) -> Match | None:
        """Update match fields (used by workers)."""
        match = self._repository.get_by_id(match_id)
        if not match:
            return None

        match.status = MatchStatus(status)

        if result is not None:
            match.result = result

        if game_state is not None:
            match.game_state = game_state

        return self._repository.save(match)

    def update_match_job(
        self,
        job_id: str,
        status: str,
        logs: str | None = None,
        result: dict[str, Any] | None = None,
        game_state: dict[str, Any] | None = None,
    ) -> MatchJob | None:
        """Update match job and sync status to match."""
        job = self._job_repository.get_match_job(job_id)
        if not job:
            return None

        job.status = status
        if logs is not None:
            job.logs += logs + "\n"
        if result is not None:
            job.result = result

        job = self._job_repository.save_match_job(job)

        # Sync with match
        self.update_match(
            str(job.match_id),
            status,
            result=result,
            game_state=game_state,
        )

        return job

    def list_matches(
        self,
        skip: int,
        limit: int,
    ) -> Sequence[Match]:
        return self._repository.list_matches(skip, limit)

    def _validate_agents_for_match(self, game_type: GameType, agent_ids: list[UUID]) -> None:
        agents = self._agent_repository.list_by_ids(agent_ids)
        if len(agents) != len(agent_ids):
            raise MatchServiceError("One or more agents were not found")

        agents_by_id = {agent.id: agent for agent in agents}
        for agent_id in agent_ids:
            agent = agents_by_id[agent_id]
            if agent.game_type != game_type:
                raise MatchServiceError(f"Agent {agent.id} does not belong to game '{game_type}'")
            if agent.active_submission is None:
                raise MatchServiceError(f"Agent {agent.id} does not have an active submission")
            if not submission_has_successful_build(agent.active_submission):
                raise MatchServiceError(f"Agent {agent.id} does not have a successful active submission")

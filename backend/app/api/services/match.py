import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.api.repositories.agent import AgentRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.match import MatchRepository
from app.api.services.submission_builds import submission_has_successful_build
from app.core.config import settings
from app.core.match_events import match_event_publisher
from app.core.queue import job_queue
from app.models.agent import Agent
from app.models.game import GameType
from app.models.job import JobStatus, MatchJob
from app.models.match import Match, MatchConfig, MatchStatus


logger = logging.getLogger(__name__)


class MatchServiceError(Exception):
    """Base exception for match service errors."""


class MatchPermissionError(MatchServiceError):
    """Raised when the caller is not allowed to use the requested agents."""


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
        config: MatchConfig,
        agent_ids: list[UUID],
        owner_user_id: UUID | None = None,
    ) -> Match:
        """
        Create a match and queue it for execution.

        If owner_user_id is given (non-admin API callers), at least one of the
        participating agents must belong to that user. Admin callers and the
        internal match scheduler pass None and may match any agents.
        """
        if config.turn_time_limit <= 0 or config.turn_time_limit > settings.MAX_TURN_TIME_LIMIT_SECONDS:
            raise MatchServiceError(f"turn_time_limit must be between 0.1 and {settings.MAX_TURN_TIME_LIMIT_SECONDS}s")

        self._validate_agents_for_match(game_type, agent_ids, owner_user_id=owner_user_id)

        config_dict = config.model_dump()
        match = Match(
            game_type=game_type, status=MatchStatus.QUEUED, config=config_dict, agent_ids=[str(i) for i in agent_ids]
        )
        match = self._repository.save(match)

        # Create job
        job = MatchJob(match_id=match.id, status=JobStatus.QUEUED)
        job = self._job_repository.save_match_job(job)

        # Enqueue job
        await job_queue.enqueue_match(match.id, match.config, job.id, match.agent_ids, job.create_images)

        return match

    def get_match(self, match_id: str) -> Match | None:
        return self._repository.get_by_id(match_id)

    async def update_match(
        self,
        match_id: str,
        status: str,
        logs: str | None = None,
        result: dict[str, Any] | None = None,
        game_state: dict[str, Any] | None = None,
    ) -> Match | None:
        """Update match fields (used by workers)."""
        match = self._repository.get_by_id(match_id)
        if not match:
            return None

        old_status = match.status

        match.status = MatchStatus(status)

        if logs is not None:
            match.logs += logs + "\n"

        if result is not None:
            match.result = result

        if game_state is not None:
            match.game_state = game_state

        match.updated_at = datetime.now(UTC)

        saved = self._repository.save(match)

        if old_status != MatchStatus.COMPLETED and saved.status == MatchStatus.COMPLETED:
            self._update_agent_stats(saved)

        # Publish game state update to Redis for SSE subscribers
        await match_event_publisher.publish_game_state(
            match_id=match_id,
            game_state=saved.game_state or {},
            status=saved.status.value,
            logs=saved.logs,
            result=saved.result,
        )

        return saved

    async def update_match_job(
        self,
        job_id: str,
        status: str,
    ) -> MatchJob | None:
        """Update match job and sync status to match."""
        job = self._job_repository.get_match_job(job_id)
        if not job:
            return None

        job.status = JobStatus(status)
        job = self._job_repository.save_match_job(job)

        # Sync status to the match
        await self.update_match(
            str(job.match_id),
            status,
        )

        return job

    def list_matches(
        self,
        skip: int,
        limit: int,
        game_type: str | None = None,
        status: MatchStatus | None = None,
    ) -> Sequence[Match]:
        return self._repository.list_matches(skip, limit, game_type=game_type, status=status)

    def _validate_agents_for_match(
        self,
        game_type: GameType,
        agent_ids: list[UUID],
        owner_user_id: UUID | None = None,
    ) -> None:
        if not (game_type.min_players <= len(agent_ids) <= game_type.max_players):
            raise MatchServiceError(
                f"Game '{game_type.value}' requires between {game_type.min_players} and "
                f"{game_type.max_players} agents. Received {len(agent_ids)}."
            )

        agents = self._agent_repository.list_by_ids(agent_ids)
        if len(agents) != len(agent_ids):
            raise MatchServiceError("One or more agents were not found")

        if owner_user_id is not None and all(agent.user_id != owner_user_id for agent in agents):
            raise MatchPermissionError("At least one participating agent must belong to you")

        agents_by_id = {agent.id: agent for agent in agents}
        for agent_id in agent_ids:
            agent = agents_by_id[agent_id]
            if agent.game_type != game_type:
                raise MatchServiceError(f"Agent {agent.id} does not belong to game '{game_type}'")
            if agent.active_submission is None:
                raise MatchServiceError(f"Agent {agent.id} does not have an active submission")
            if not submission_has_successful_build(agent.active_submission):
                raise MatchServiceError(f"Agent {agent.id} does not have a successful active submission")

    def _update_agent_stats(self, match: Match) -> None:
        """Update agent stats for a match."""
        logger.info(f"Updating agent stats for match {match.id}. Result: {match.result}")
        if not match.result or "winner" not in match.result:
            logger.warning(f"Match {match.id} has no result or winner. Skipping stats update.")
            return

        agents_by_id = self._fetch_agents_by_ids(match.agent_ids)
        if not agents_by_id:
            return

        winner = match.result.get("winner")
        winner_str = str(winner) if winner and winner != "draw" else None

        self._update_basic_stats(match.agent_ids, agents_by_id, winner, winner_str)
        self._update_elo_stats(match.agent_ids, agents_by_id, winner, winner_str)

        for agent in agents_by_id.values():
            agent.updated_at = datetime.now(UTC)
            self._agent_repository.save(agent)
            logger.info(f"Saved stats for agent {agent.id}")

    def _fetch_agents_by_ids(self, agent_ids: list[UUID] | list[str]) -> dict[str, Agent]:
        """Fetch agents by their IDs and return a mapping."""
        agent_uuids: list[UUID] = []
        for aid in agent_ids:
            if isinstance(aid, UUID):
                agent_uuids.append(aid)
            else:
                try:
                    agent_uuids.append(UUID(aid))
                except ValueError:
                    logger.exception(f"Failed to parse agent ID as UUID: {aid}")
                    continue

        if not agent_uuids:
            return {}

        agents = self._agent_repository.list_by_ids(agent_uuids)
        return {str(a.id): a for a in agents}

    def _update_basic_stats(
        self, agent_ids: list[UUID] | list[str], agents_by_id: dict[str, Agent], winner: Any, winner_str: str | None
    ) -> None:
        """Update matches_played, wins, losses, and draws for agents."""
        for a_id in agent_ids:
            a_id_str = str(a_id)
            agent = agents_by_id.get(a_id_str)
            if not agent:
                logger.exception(f"Agent {a_id_str} not found in database")
                continue

            agent.matches_played += 1
            if winner == "draw":
                agent.draws += 1
                logger.info(f"Agent {a_id_str} recorded a draw")
            elif winner_str == a_id_str:
                agent.wins += 1
                logger.info(f"Agent {a_id_str} recorded a win")
            else:
                agent.losses += 1
                logger.info(f"Agent {a_id_str} recorded a loss (winner was {winner_str})")

    def _update_elo_stats(
        self, agent_ids: list[UUID] | list[str], agents_by_id: dict[str, Agent], winner: Any, winner_str: str | None
    ) -> None:
        """Calculate and update Elo ratings for a 1v1 match."""
        if len(agent_ids) != 2:  # noqa: PLR2004
            return

        a_id1, a_id2 = str(agent_ids[0]), str(agent_ids[1])
        if a_id1 == a_id2:
            return

        agent1 = agents_by_id.get(a_id1)
        agent2 = agents_by_id.get(a_id2)

        if not (agent1 and agent2):
            return

        elo1 = agent1.elo if agent1.elo is not None else 1200
        elo2 = agent2.elo if agent2.elo is not None else 1200

        score1 = 0.5
        if winner == "draw":
            score1 = 0.5
        elif winner_str == a_id1:
            score1 = 1.0
        elif winner_str == a_id2:
            score1 = 0.0

        agent1.elo, agent2.elo = self._calculate_elo_update(elo1, elo2, score1)
        logger.info(f"Elo updated: Agent {a_id1} ({elo1} -> {agent1.elo}), Agent {a_id2} ({elo2} -> {agent2.elo})")

    def _calculate_elo_update(self, elo1: float, elo2: float, score1: float, k_factor: int = 32) -> tuple[int, int]:
        """
        Calculate new Elo ratings for two agents.

        Args:
            elo1: Current Elo of agent 1.
            elo2: Current Elo of agent 2.
            score1: Score of agent 1 (1.0 for win, 0.5 for draw, 0.0 for loss).
            k_factor: K-factor for Elo calculation.

        Returns:
            Tuple of (new_elo1, new_elo2).
        """
        expected1 = 1 / (1 + 10 ** ((elo2 - elo1) / 400))
        expected2 = 1 - expected1

        score2 = 1.0 - score1

        new_elo1 = int(elo1 + k_factor * (score1 - expected1))
        new_elo2 = int(elo2 + k_factor * (score2 - expected2))

        return new_elo1, new_elo2

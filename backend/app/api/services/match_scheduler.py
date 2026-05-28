import logging
import random
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlmodel import Session

from app.api.repositories.agent import AgentRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.match import MatchRepository
from app.api.services.match import MatchService
from app.api.services.submission_builds import submission_has_successful_build
from app.core.config import settings
from app.db.connection import engine
from app.models.agent import Agent
from app.models.game import GameType
from app.models.match import MatchConfig, MatchStatus


logger = logging.getLogger(__name__)


class MatchSchedulerService:
    """
    Manages the scheduling of matches based on certain criteria.
    """

    def __init__(self) -> None:
        self.strategy = "least_played"

    async def check_and_queue_matches(self) -> None:
        """
        Check if new matches need to be queued and enqueue them if necessary.
        This method can be called periodically by a background task.
        """
        logger.info(f"Checking if new matches need to be queued (Strategy: {self.strategy})...")

        with Session(engine) as session:
            match_repository = MatchRepository(session)
            agent_repository = AgentRepository(session)
            job_repository = JobRepository(session)
            match_service = MatchService(match_repository, job_repository, agent_repository)

            await self._fail_stale_running_matches(match_repository, match_service)

            # Check the current match queue and determine if new matches should be added
            if not self._check_match_queue(match_repository):
                logger.info("No new matches need to be queued at this time.")
                return

            # Get available agents that can be scheduled for matches
            available_agents = self._get_available_agents(agent_repository)

            # remove game types with less than 2 available agents
            available_agents = {game_type: agents for game_type, agents in available_agents.items() if len(agents) >= 2}  # noqa: PLR2004
            if not available_agents:
                logger.info("No game types have enough available agents to schedule matches.")
                return

            # randomly choose a game type
            game_type_str = random.choice(list(available_agents.keys()))  # noqa: S311
            agents_for_match = self._choose_agents_for_match(available_agents[game_type_str])

            # Create and enqueue a new match with the selected agents
            try:
                game_type = GameType(game_type_str)
                config = MatchConfig()
                match = await match_service.create_match(
                    game_type=game_type,
                    config=config,
                    agent_ids=agents_for_match,
                )
                logger.info(
                    f"Queued a new match for game type '{game_type_str}' with agents: {agents_for_match}, "
                    f"match_id: {match.id}"
                )
            except Exception:
                logger.exception(f"Error creating match for game type '{game_type_str}' with agents {agents_for_match}")

    def _check_match_queue(self, match_repository: MatchRepository) -> bool:
        """
        Check the current match queue and determine if new matches should be added.
        Matches are added as long as no match is in queue or running for any game type.
        """
        # Check if any matches are currently queued
        queued_matches = match_repository.list_matches(skip=0, limit=1, status=MatchStatus.QUEUED.value)
        if queued_matches:
            return False

        # Check if any matches are currently running
        running_matches = match_repository.list_matches(skip=0, limit=1, status=MatchStatus.RUNNING.value)

        return not running_matches

    async def _fail_stale_running_matches(
        self,
        match_repository: MatchRepository,
        match_service: MatchService,
    ) -> None:
        """
        Recover matches abandoned by a killed/restarted worker.

        The match runner sets a match to RUNNING before executing it. If that process or
        its backend connection dies before publishing a terminal status, the scheduler's
        queue gate would otherwise see RUNNING forever and stop scheduling new matches.
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.MATCH_STALE_TIMEOUT_SECONDS)
        stale_matches = match_repository.list_stale_running_matches(cutoff=cutoff)
        for match in stale_matches:
            logger.warning(
                "Marking stale running match %s as failed; last update at %s exceeded %ss timeout",
                match.id,
                match.updated_at,
                settings.MATCH_STALE_TIMEOUT_SECONDS,
            )
            await match_service.update_match(
                str(match.id),
                status=MatchStatus.FAILED.value,
                result={
                    "status": "error",
                    "reason": "Match runner lost or timed out",
                    "details": (
                        "Match remained in running state without worker updates beyond "
                        f"{settings.MATCH_STALE_TIMEOUT_SECONDS} seconds."
                    ),
                },
            )

    def _get_available_agents(self, agent_repository: AgentRepository) -> dict[GameType, list[Agent]]:
        """
        Get a list of available agents that can be scheduled for matches.
        Returns a dictionary of game type to Agent objects.
        """
        # Get all agents, fetching in batches
        available_by_game_type: dict[GameType, list[Agent]] = defaultdict(list)

        skip = 0
        limit = 100

        while True:
            agents, total = agent_repository.list_agents(skip=skip, limit=limit)
            if not agents:
                break

            # Filter agents that have active submissions with successful builds
            for agent in agents:
                if agent.active_submission and submission_has_successful_build(agent.active_submission):
                    available_by_game_type[agent.game_type].append(agent)

            skip += limit
            if skip >= total:
                break

        return dict(available_by_game_type)

    def _choose_agents_for_match(self, available_agents: list[Agent]) -> list[UUID]:
        """
        Choose a set of agents to participate in a new match based on strategy.
        """
        if self.strategy == "least_played":
            # Shuffle first to handle ties randomly (Python's sort is stable)
            shuffled_agents = list(available_agents)
            random.shuffle(shuffled_agents)
            # Sort by matches_played and take the first two
            sorted_agents = sorted(shuffled_agents, key=lambda a: a.matches_played)
            chosen = sorted_agents[:2]
        else:
            # Default: random
            chosen = random.sample(available_agents, 2)

        return [agent.id for agent in chosen]

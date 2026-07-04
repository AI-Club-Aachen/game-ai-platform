import logging
import random
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlmodel import Session

from app.api.repositories.agent import AgentRepository
from app.api.repositories.arena import ArenaRepository
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


# How many matches to queue per tick: "serial" keeps one in flight, "concurrent"
# fills up to settings.MATCH_MAX_CONCURRENT_MATCHES.
SCHEDULING_SERIAL = "serial"
SCHEDULING_CONCURRENT = "concurrent"
VALID_SCHEDULING_STRATEGIES = {SCHEDULING_SERIAL, SCHEDULING_CONCURRENT}


class MatchSchedulerService:
    """
    Manages the scheduling of matches based on certain criteria.
    """

    def __init__(self) -> None:
        # Which agents to pair for a new match.
        self.strategy = "least_played"
        # How many matches to keep in flight (see constants above).
        self.scheduling_strategy = SCHEDULING_SERIAL

    async def check_and_queue_matches(self) -> None:
        """
        Check if new matches need to be queued and enqueue them if necessary.
        This method can be called periodically by a background task.
        """
        logger.info(
            "Checking if new matches need to be queued "
            f"(Selection: {self.strategy}, Scheduling: {self.scheduling_strategy})..."
        )

        with Session(engine) as session:
            match_repository = MatchRepository(session)
            agent_repository = AgentRepository(session)
            job_repository = JobRepository(session)
            arena_repository = ArenaRepository(session)
            match_service = MatchService(match_repository, job_repository, agent_repository, arena_repository)

            await self._fail_stale_running_matches(match_repository, match_service)

            free_slots = self._free_slots(match_repository)
            if free_slots <= 0:
                logger.info("No new matches need to be queued at this time.")
                return

            # Get available agents grouped by arena
            available_agents = self._get_available_agents_by_arena(agent_repository)

            # remove arenas with less than 2 available agents
            available_agents = {arena_id: agents for arena_id, agents in available_agents.items() if len(agents) >= 2}  # noqa: PLR2004
            if not available_agents:
                logger.info("No arenas have enough available agents to schedule matches.")
                return

            # Provisional per-tick counts so a batch spreads across agents instead of
            # repeatedly picking the same least-played pairing (QUEUED matches don't
            # update matches_played until they finish).
            local_played: dict[UUID, int] = defaultdict(int)

            for _ in range(free_slots):
                arena_id = random.choice(list(available_agents.keys()))  # noqa: S311
                agents_for_match = self._choose_agents_for_match(
                    available_agents[arena_id], local_played
                )
                for agent_id in agents_for_match:
                    local_played[agent_id] += 1

                # Create and enqueue a new match for the selected arena
                try:
                    config = MatchConfig()
                    match = await match_service.create_match(
                        arena_id=arena_id,
                        config=config,
                        agent_ids=agents_for_match,
                    )
                    logger.info(
                        f"Queued a new match for arena '{arena_id}' with agents: {agents_for_match}, "
                        f"match_id: {match.id}"
                    )
                except Exception:
                    logger.exception(
                        f"Error creating match for arena '{arena_id}' with agents {agents_for_match}"
                    )

    def _free_slots(self, match_repository: MatchRepository) -> int:
        """
        Number of additional non-tournament matches to queue this tick, per the
        active scheduling strategy.
        """
        if self.scheduling_strategy == SCHEDULING_CONCURRENT:
            return self._available_match_slots(match_repository)
        # Default / legacy serial behaviour: one match at a time.
        return 1 if self._check_match_queue(match_repository) else 0

    def _available_match_slots(self, match_repository: MatchRepository) -> int:
        """Concurrent strategy: free slots below the configured concurrency target."""
        in_flight = match_repository.count_active_non_tournament()
        return settings.MATCH_MAX_CONCURRENT_MATCHES - in_flight

    def _check_match_queue(self, match_repository: MatchRepository) -> bool:
        """
        Serial-strategy gate: only queue a new match when no non-tournament match is
        currently queued or running. Tournament matches are ignored here.
        """
        queued_matches = match_repository.list_matches(
            skip=0, limit=1, status=MatchStatus.QUEUED.value, with_tournament=False
        )
        if queued_matches:
            return False

        running_matches = match_repository.list_matches(
            skip=0, limit=1, status=MatchStatus.RUNNING.value, with_tournament=False
        )

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
        Stale tournament matches are recovered by the tournament scheduler instead.
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.MATCH_STALE_TIMEOUT_SECONDS)
        stale_matches = match_repository.list_stale_running_matches(cutoff=cutoff, with_tournament=False)
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

    def _get_available_agents_by_arena(self, agent_repository: AgentRepository) -> dict[UUID, list[Agent]]:
        """
        Get a list of available agents that can be scheduled for matches.
        Returns a dictionary of arena ID to Agent objects.
        """
        # Get all agents, fetching in batches
        available_by_arena: dict[UUID, list[Agent]] = defaultdict(list)

        skip = 0
        limit = 100

        while True:
            agents, total = agent_repository.list_agents(skip=skip, limit=limit)
            if not agents:
                break

            # Filter agents that have active submissions with successful builds
            for agent in agents:
                if agent.active_submission and submission_has_successful_build(agent.active_submission):
                    available_by_arena[agent.arena_id].append(agent)

            skip += limit
            if skip >= total:
                break

        return dict(available_by_arena)

    def _choose_agents_for_match(
        self,
        available_agents: list[Agent],
        local_played: dict[UUID, int] | None = None,
    ) -> list[UUID]:
        """
        Choose a set of agents to participate in a new match based on strategy.

        ``local_played`` adds provisional counts for agents already picked this tick.
        """
        local_played = local_played or {}
        if self.strategy == "least_played":
            # Shuffle first to handle ties randomly (Python's sort is stable)
            shuffled_agents = list(available_agents)
            random.shuffle(shuffled_agents)
            # Sort by effective matches played (persisted + provisional this tick)
            sorted_agents = sorted(
                shuffled_agents,
                key=lambda a: a.matches_played + local_played.get(a.id, 0),
            )
            chosen = sorted_agents[:2]
        else:
            # Default: random
            chosen = random.sample(available_agents, 2)

        return [agent.id for agent in chosen]

import logging
import random
from collections import defaultdict
from uuid import UUID

from sqlmodel import Session

from app.api.repositories.agent import AgentRepository
from app.api.repositories.arena import ArenaRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.match import MatchRepository
from app.api.services.match import MatchService
from app.core.config import settings
from app.db.connection import engine
from app.models.agent import Agent
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
        # Human-vs-agent limits; kept here so admins edit them with the other settings.
        self.human_move_time_limit = settings.HUMAN_MOVE_TIME_LIMIT_SECONDS
        self.human_match_max_duration = settings.HUMAN_MATCH_MAX_DURATION_SECONDS

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

            # Otherwise the queue gate sees an abandoned match as RUNNING forever.
            await match_service.fail_stale_running_matches(with_tournament=False)

            free_slots = self._free_slots(match_repository)
            if free_slots <= 0:
                logger.info("No new matches need to be queued at this time.")
                return

            # Get available agents grouped by arena
            available_agents = self._get_available_agents_by_arena(match_service)

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
        currently queued or running. Tournament and human-vs-agent matches are ignored here.
        """
        queued_matches = match_repository.list_matches(
            skip=0, limit=1, status=MatchStatus.QUEUED.value, with_tournament=False, with_human=False
        )
        if queued_matches:
            return False

        running_matches = match_repository.list_matches(
            skip=0, limit=1, status=MatchStatus.RUNNING.value, with_tournament=False, with_human=False
        )

        return not running_matches

    @staticmethod
    def _get_available_agents_by_arena(match_service: MatchService) -> dict[UUID, list[Agent]]:
        """Playable agents (working active build) grouped by arena ID."""
        available_by_arena: dict[UUID, list[Agent]] = defaultdict(list)
        for agent, _owner in match_service.list_playable_agents():
            available_by_arena[agent.arena_id].append(agent)
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

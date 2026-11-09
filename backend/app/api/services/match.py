import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.api.repositories.agent import AgentRepository
from app.api.repositories.arena import ArenaRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.match import MatchRepository
from app.api.services.submission_builds import submission_has_successful_build
from app.core.config import settings
from app.core.match_events import match_event_publisher
from app.core.payload_limits import PayloadTooLargeError, cap_log_append, ensure_json_within
from app.core.queue import job_queue
from app.core.state_init import StateInitValidationError, validate_state_init_data
from app.models.agent import Agent
from app.models.arena import Arena
from app.models.game import GameType
from app.models.job import JobStatus, MatchJob
from app.models.match import Match, MatchConfig, MatchStatus


logger = logging.getLogger(__name__)


class MatchServiceError(Exception):
    """Base exception for match service errors."""


class MatchPermissionError(MatchServiceError):
    """Raised when the caller is not allowed to use the requested agents."""


class MatchNotFoundError(MatchServiceError):
    """Raised when the requested match does not exist."""


class MatchConflictError(MatchServiceError):
    """Raised when the request conflicts with the match's current state (e.g. not your turn)."""


# Upper bound on a submitted human move's JSON size; real moves are tiny.
MAX_HUMAN_MOVE_BYTES = 1024


class MatchPayloadTooLargeError(MatchServiceError):
    """Raised when a worker-supplied result/game-state payload exceeds its cap (M-3)."""


class MatchService:
    """Service for managing matches."""

    def __init__(
        self,
        match_repository: MatchRepository,
        job_repository: JobRepository,
        agent_repository: AgentRepository,
        arena_repository: ArenaRepository,
    ) -> None:
        self._repository = match_repository
        self._job_repository = job_repository
        self._agent_repository = agent_repository
        self._arena_repository = arena_repository

    async def create_match(
        self,
        arena_id: UUID,
        config: MatchConfig,
        agent_ids: list[UUID],
        owner_user_id: UUID | None = None,
        tournament_id: UUID | None = None,
    ) -> Match:
        """
        Create a match and queue it for execution.

        If owner_user_id is given (non-admin API callers), at least one of the
        participating agents must belong to that user. Admin callers and the
        internal match scheduler pass None and may match any agents.

        tournament_id tags a match as tournament play (set only by the
        tournament engine): such matches skip global agent stats and are
        ignored by the random auto-scheduler.
        """
        arena = self._get_active_arena(arena_id)
        game_type = arena.game_type

        # Human-play limits are server-controlled; never accept them from API input.
        config.human_turn_time_limit = None
        config.max_duration_seconds = None
        self._apply_arena_config(arena, config)

        self._validate_agents_for_match(arena_id, game_type, agent_ids, owner_user_id=owner_user_id)

        config_dict = config.model_dump()
        match = Match(
            game_type=game_type,
            arena_id=arena_id,
            status=MatchStatus.QUEUED,
            config=config_dict,
            agent_ids=[str(i) for i in agent_ids],
            tournament_id=tournament_id,
        )
        match = self._repository.save(match)

        # Create job
        job = MatchJob(match_id=match.id, status=JobStatus.QUEUED)
        job = self._job_repository.save_match_job(job)

        # Enqueue job
        await job_queue.enqueue_match(match.id, match.config, job.id, match.agent_ids, job.create_images)

        return match

    def _get_active_arena(self, arena_id: UUID) -> Arena:
        arena = self._arena_repository.get_by_id(arena_id)
        if not arena or not arena.is_active:
            raise MatchServiceError("Target arena not found or inactive")
        return arena

    @staticmethod
    def _apply_arena_config(arena: Arena, config: MatchConfig) -> None:
        """Merge per-game defaults and arena config into ``config`` and validate it."""
        game_type = arena.game_type
        merged_state_init = dict(game_type.additional_data)
        merged_state_init.update({k: v for k, v in arena.config.items() if k != "turn_time_limit"})
        merged_state_init.update(config.state_init_data)
        config.state_init_data = merged_state_init

        if "turn_time_limit" in arena.config:
            config.turn_time_limit = arena.config["turn_time_limit"]

        if config.turn_time_limit <= 0 or config.turn_time_limit > settings.MAX_TURN_TIME_LIMIT_SECONDS:
            raise MatchServiceError(f"turn_time_limit must be between 0.1 and {settings.MAX_TURN_TIME_LIMIT_SECONDS}s")

        # Validate state_init_data per game (treat as untrusted).
        try:
            validate_state_init_data(game_type, config.state_init_data)
        except StateInitValidationError as e:
            raise MatchServiceError(str(e)) from e

    # --- Human-vs-agent play ---------------------------------------------

    async def create_human_match(
        self,
        arena_id: UUID,
        agent_id: UUID,
        human_user_id: UUID,
        human_name: str,
        human_player_index: int,
        human_turn_time_limit: float,
        max_duration_seconds: float,
    ) -> Match:
        """
        Start a match where ``human_user_id`` plays by hand against one agent.

        Any agent of the arena with a working build may be challenged. A user may
        have only one queued/running human match at a time (it occupies a match
        runner while waiting on them). The result never touches agent stats/ELO.
        """
        arena = self._get_active_arena(arena_id)
        game_type = arena.game_type
        if not (game_type.min_players <= 2 <= game_type.max_players):  # noqa: PLR2004
            raise MatchServiceError(f"Game '{game_type.value}' does not support 1v1 human play")
        if human_player_index not in (0, 1):
            raise MatchServiceError("human_player_index must be 0 or 1")

        config = MatchConfig(
            human_turn_time_limit=human_turn_time_limit,
            max_duration_seconds=max_duration_seconds,
        )
        self._apply_arena_config(arena, config)
        self._check_agents_eligible(arena_id, game_type, [agent_id])

        await self._ensure_no_active_human_match(human_user_id)

        match = Match(
            game_type=game_type,
            arena_id=arena_id,
            status=MatchStatus.QUEUED,
            config=config.model_dump(),
            agent_ids=[str(agent_id)],
            human_user_id=human_user_id,
            human_player_index=human_player_index,
            human_name=human_name,
        )
        match = self._repository.save(match)

        job = MatchJob(match_id=match.id, status=JobStatus.QUEUED)
        job = self._job_repository.save_match_job(job)
        await job_queue.enqueue_match(match.id, match.config, job.id, match.agent_ids, job.create_images)
        return match

    def list_human_opponents(self, arena_id: UUID, user_id: UUID) -> list[dict[str, Any]]:
        """Agents of the arena that can be challenged (active submission with a successful build)."""
        arena = self._get_active_arena(arena_id)
        opponents = []
        for agent, username in self._agent_repository.list_by_arena_with_owner(arena.id):
            if agent.active_submission is None or not submission_has_successful_build(agent.active_submission):
                continue
            opponents.append(
                {
                    "id": str(agent.id),
                    "agent_name": agent.name,
                    "username": username,
                    "elo": agent.elo,
                    "is_mine": agent.user_id == user_id,
                }
            )
        # Own agents first, then by ELO (unrated last).
        opponents.sort(key=lambda o: (not o["is_mine"], -(o["elo"] if o["elo"] is not None else -1)))
        return opponents

    def get_agent_names(self, agent_ids: list[UUID] | list[str]) -> dict[str, str]:
        """Display names for a match's agents (already public via leaderboards)."""
        return {agent_id: agent.name for agent_id, agent in self._fetch_agents_by_ids(agent_ids).items()}

    async def _ensure_no_active_human_match(self, user_id: UUID) -> None:
        """
        Enforce one active human match per user. A running match whose worker
        stopped reporting (crash/restart) is failed here so it can't lock the user
        out when the auto-scheduler's stale recovery isn't running.
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.MATCH_STALE_TIMEOUT_SECONDS)
        for active in self._repository.list_active_human_matches(user_id):
            updated_at = active.updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)
            if active.status == MatchStatus.RUNNING and updated_at < cutoff:
                logger.warning("Failing stale human match %s (last update %s)", active.id, active.updated_at)
                await self.update_match(
                    str(active.id),
                    status=MatchStatus.FAILED.value,
                    result={"status": "error", "reason": "Match runner lost or timed out"},
                )
                continue
            raise MatchConflictError(
                f"You already have an active game ({active.id}). Finish or resign it first."
            )

    def _get_own_human_match(self, match_id: str, user_id: UUID) -> Match:
        match = self._repository.get_by_id(match_id)
        if not match:
            raise MatchNotFoundError("Match not found")
        if match.human_user_id is None or match.human_user_id != user_id:
            raise MatchPermissionError("You are not the human player in this match")
        return match

    async def submit_human_move(self, match_id: str, user_id: UUID, move: dict[str, Any]) -> None:
        """
        Forward the human player's move to the match runner. Full rule validation
        happens in the worker (gamelib engine); an illegal move is rejected there
        without forfeiting, and the human keeps their turn.
        """
        match = self._get_own_human_match(match_id, user_id)
        if match.status != MatchStatus.RUNNING:
            raise MatchConflictError("Match is not running")
        state = match.game_state or {}
        if state.get("turn") != match.human_player_index:
            raise MatchConflictError("It is not your turn")
        try:
            ensure_json_within(move, max_bytes=MAX_HUMAN_MOVE_BYTES, field_name="move")
        except PayloadTooLargeError as e:
            raise MatchPayloadTooLargeError(str(e)) from e

        payload_move = {**move, "player": match.human_player_index}
        await job_queue.push_human_move(match.id, {"type": "move", "move": payload_move})

    async def resign_human_match(self, match_id: str, user_id: UUID) -> Match:
        """
        Resign a human match. A queued match is cancelled directly (the worker skips
        matches that are no longer queued); a running one is resigned by the worker.
        """
        match = self._get_own_human_match(match_id, user_id)
        if match.status == MatchStatus.QUEUED:
            updated = await self.update_match(
                str(match.id),
                status=MatchStatus.FAILED.value,
                logs="[ABORT] Cancelled by player before start",
                result={"status": "error", "reason": "Cancelled by player"},
            )
            return updated or match
        if match.status != MatchStatus.RUNNING:
            raise MatchConflictError("Match is already over")
        await job_queue.push_human_move(match.id, {"type": "resign"})
        return match

    def get_match(self, match_id: str) -> Match | None:
        return self._repository.get_by_id(match_id)

    async def get_human_move_remaining(self, match: Match) -> float | None:
        """Authoritative seconds left for the human's pending move (None if none)."""
        if match.human_user_id is None or match.status != MatchStatus.RUNNING:
            return None
        return await match_event_publisher.get_human_move_remaining(str(match.id))

    @staticmethod
    def _reject_oversized(payload: dict[str, Any], *, max_bytes: int, field_name: str) -> None:
        """Reject a worker-supplied JSON payload that exceeds its configured cap (M-3)."""
        try:
            ensure_json_within(payload, max_bytes=max_bytes, field_name=field_name)
        except PayloadTooLargeError as e:
            raise MatchPayloadTooLargeError(str(e)) from e

    async def update_match(
        self,
        match_id: str,
        status: str,
        logs: str | None = None,
        result: dict[str, Any] | None = None,
        game_state: dict[str, Any] | None = None,
        human_turn_seconds: float | None = None,
    ) -> Match | None:
        """Update match fields (used by workers)."""
        match = self._repository.get_by_id(match_id)
        if not match:
            return None

        old_status = match.status

        match.status = MatchStatus(status)

        if logs is not None:
            # Truncate stored logs server-side so a worker cannot grow them without bound.
            match.logs = cap_log_append(
                match.logs,
                logs,
                append_cap=settings.MAX_LOG_APPEND_BYTES,
                total_cap=settings.MAX_TOTAL_LOG_BYTES,
            )

        if result is not None:
            self._reject_oversized(result, max_bytes=settings.MAX_RESULT_BYTES, field_name="result")
            match.result = result

        if game_state is not None:
            self._reject_oversized(game_state, max_bytes=settings.MAX_GAME_STATE_BYTES, field_name="game_state")
            match.game_state = game_state

        match.updated_at = datetime.now(UTC)

        saved = self._repository.save(match)

        # Tournament matches never touch global agent stats/ELO; tournament
        # standings live in the tournament tables.
        became_completed = old_status != MatchStatus.COMPLETED and saved.status == MatchStatus.COMPLETED
        # Human-vs-agent matches don't count either (anyone could farm wins/losses).
        if became_completed and saved.tournament_id is None and saved.human_user_id is None:
            self._update_agent_stats(saved)

        if saved.human_user_id is not None:
            # A new state means the pending move (if any) was played; the runner
            # reports the next human deadline when it starts waiting again.
            if game_state is not None or saved.status != MatchStatus.RUNNING:
                await match_event_publisher.clear_human_deadline(match_id)
            if human_turn_seconds is not None and saved.status == MatchStatus.RUNNING:
                await match_event_publisher.set_human_deadline(match_id, human_turn_seconds)

        # Publish game state update to Redis for SSE subscribers
        await match_event_publisher.publish_game_state(
            match_id=match_id,
            game_state=saved.game_state or {},
            status=saved.status.value,
            logs=saved.logs,
            result=saved.result,
            human_move_remaining=await self.get_human_move_remaining(saved),
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
        arena_id: UUID | None = None,
        status: list[str] | MatchStatus | None = None,
    ) -> Sequence[Match]:
        return self._repository.list_matches(skip, limit, game_type=game_type, arena_id=arena_id, status=status)

    def _validate_agents_for_match(
        self,
        arena_id: UUID,
        game_type: GameType,
        agent_ids: list[UUID],
        owner_user_id: UUID | None = None,
    ) -> None:
        if not (game_type.min_players <= len(agent_ids) <= game_type.max_players):
            raise MatchServiceError(
                f"Game '{game_type.value}' requires between {game_type.min_players} and "
                f"{game_type.max_players} agents. Received {len(agent_ids)}."
            )

        agents = self._check_agents_eligible(arena_id, game_type, agent_ids)

        if owner_user_id is not None and all(agent.user_id != owner_user_id for agent in agents):
            raise MatchPermissionError("At least one participating agent must belong to you")

    def _check_agents_eligible(self, arena_id: UUID, game_type: GameType, agent_ids: list[UUID]) -> list[Agent]:
        """Every agent must exist, belong to the arena/game and have a successful active build."""
        agents = self._agent_repository.list_by_ids(agent_ids)
        if len(agents) != len(agent_ids):
            raise MatchServiceError("One or more agents were not found")

        agents_by_id = {agent.id: agent for agent in agents}
        for agent_id in agent_ids:
            agent = agents_by_id[agent_id]
            if agent.arena_id != arena_id:
                raise MatchServiceError(f"Agent {agent.id} does not belong to the target arena")
            if agent.game_type != game_type:
                raise MatchServiceError(f"Agent {agent.id} does not belong to game '{game_type}'")
            if agent.active_submission is None:
                raise MatchServiceError(f"Agent {agent.id} does not have an active submission")
            if not submission_has_successful_build(agent.active_submission):
                raise MatchServiceError(f"Agent {agent.id} does not have a successful active submission")
        return agents

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

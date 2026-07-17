import logging
import random
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import UUID

from app.api.repositories.agent import AgentRepository
from app.api.repositories.arena import ArenaRepository
from app.api.repositories.match import MatchRepository
from app.api.repositories.tournament import TournamentRepository
from app.api.services.match import MatchService, MatchServiceError
from app.api.services.submission_builds import submission_has_successful_build
from app.api.services.tournament_bracket import (
    MatchupSpec,
    deterministic_coin_flip,
    game_agent_order,
    generate_double_elimination_bracket,
)
from app.core.config import settings
from app.core.state_init import StateInitValidationError, validate_state_init_data
from app.models.game import GameType
from app.models.match import Match, MatchConfig, MatchStatus
from app.models.tournament import (
    BracketSide,
    GameResolution,
    MatchupStatus,
    SlotSourceRole,
    Tournament,
    TournamentConfig,
    TournamentEntrant,
    TournamentGame,
    TournamentMatchup,
    TournamentStatus,
)


logger = logging.getLogger(__name__)

GAMES_TO_WIN_MATCHUP = 2
# The first two games run in parallel; the decider is created only on a 1-1 split.
PARALLEL_GAME_INDICES = (0, 1)
DECIDER_GAME_INDEX = 2

_TERMINAL_MATCHUP_STATUSES = {MatchupStatus.COMPLETED, MatchupStatus.CANCELLED}
_TERMINAL_MATCH_STATUSES = {MatchStatus.COMPLETED, MatchStatus.FAILED, MatchStatus.CLIENT_ERROR}


class TournamentServiceError(Exception):
    """Base exception for tournament service errors (maps to 400)."""


class TournamentNotFoundError(TournamentServiceError):
    """Raised when a tournament or matchup does not exist (maps to 404)."""


class TournamentStateError(TournamentServiceError):
    """Raised when an operation is invalid for the current state (maps to 409)."""


class TournamentService:
    """Service for managing double-elimination tournaments."""

    MIN_ENTRANTS: ClassVar[int] = 2
    MAX_CONCURRENT_HARD_CAP: ClassVar[int] = 64

    def __init__(
        self,
        tournament_repository: TournamentRepository,
        match_repository: MatchRepository,
        agent_repository: AgentRepository,
        match_service: MatchService,
        arena_repository: ArenaRepository,
    ) -> None:
        self._repository = tournament_repository
        self._match_repository = match_repository
        self._agent_repository = agent_repository
        self._match_service = match_service
        self._arena_repository = arena_repository

    # --- Queries ---

    def get_tournament(self, tournament_id: UUID) -> Tournament | None:
        return self._repository.get_by_id(tournament_id)

    def list_tournaments(
        self,
        skip: int,
        limit: int,
        game_type: str | None = None,
        arena_id: UUID | None = None,
        status: TournamentStatus | None = None,
    ) -> Sequence[Tournament]:
        return self._repository.list_tournaments(skip, limit, game_type=game_type, arena_id=arena_id, status=status)

    def get_bracket(self, tournament_id: UUID) -> dict[str, Any]:
        """Full bracket view: tournament, entrants, matchups with games, and standings."""
        tournament = self._repository.get_by_id(tournament_id)
        if not tournament:
            raise TournamentNotFoundError("Tournament not found")

        entrants = self._repository.list_entrants(tournament_id)
        matchups = self._repository.list_matchups(tournament_id)
        games = self._repository.list_games(tournament_id)

        games_by_matchup: dict[UUID, list[TournamentGame]] = {}
        for game in games:
            games_by_matchup.setdefault(game.matchup_id, []).append(game)

        # Agent display names, so read-only clients need no extra agent queries.
        agents = self._agent_repository.list_by_ids([entrant.agent_id for entrant in entrants])
        agent_names = {agent.id: agent.name for agent in agents}

        return {
            "tournament": tournament,
            "entrants": [
                {
                    "agent_id": entrant.agent_id,
                    "seed": entrant.seed,
                    "agent_name": agent_names.get(entrant.agent_id),
                }
                for entrant in entrants
            ],
            "matchups": [
                {
                    "matchup": matchup,
                    "games": sorted(games_by_matchup.get(matchup.id, []), key=lambda g: g.game_index),
                }
                for matchup in matchups
            ],
            "standings": self._compute_standings(tournament, entrants, matchups, agent_names),
        }

    # --- Commands ---

    def create_tournament(
        self,
        name: str,
        arena_id: UUID,
        agent_ids: list[UUID],
        config: TournamentConfig,
    ) -> Tournament:
        """Create a tournament with an admin-curated set of entrant agents."""
        arena = self._arena_repository.get_by_id(arena_id)
        if not arena or not arena.is_active:
            raise TournamentServiceError("Target arena not found or inactive")
        game_type = arena.game_type

        # Merge arena config into tournament config
        if "turn_time_limit" in arena.config:
            config.turn_time_limit = arena.config["turn_time_limit"]

        for k, v in arena.config.items():
            if k != "turn_time_limit" and k not in config.state_init_data:
                config.state_init_data[k] = v

        self._validate_config(game_type, config)
        self._validate_entrants_per_arena(arena_id, game_type, agent_ids)

        tournament = Tournament(
            name=name,
            game_type=game_type,
            arena_id=arena_id,
            status=TournamentStatus.PENDING,
            config=config.model_dump(),
        )
        tournament = self._repository.save(tournament)

        for agent_id in agent_ids:
            self._repository.save_entrant(TournamentEntrant(tournament_id=tournament.id, agent_id=agent_id))

        return tournament

    async def start_tournament(self, tournament_id: UUID) -> Tournament:
        """Randomly seed the bracket and queue the first round."""
        tournament = self._repository.get_by_id(tournament_id)
        if not tournament:
            raise TournamentNotFoundError("Tournament not found")
        if tournament.status != TournamentStatus.PENDING:
            raise TournamentStateError(f"Tournament cannot be started from status '{tournament.status.value}'")

        entrants = list(self._repository.list_entrants(tournament_id))
        if len(entrants) < self.MIN_ENTRANTS:
            raise TournamentServiceError(f"Tournament requires at least {self.MIN_ENTRANTS} entrants")

        specs = generate_double_elimination_bracket(
            [entrant.agent_id for entrant in entrants],
            random.Random(),  # noqa: S311 - seeding randomness, not security-sensitive
        )

        now = datetime.now(UTC)
        matchups = [
            TournamentMatchup(
                id=spec.id,
                tournament_id=tournament.id,
                bracket=spec.bracket,
                round=spec.round,
                position=spec.position,
                stage=spec.stage,
                agent1_id=spec.agent1_id,
                agent2_id=spec.agent2_id,
                slot1_source_matchup_id=spec.slot1_source.matchup_id if spec.slot1_source else None,
                slot1_source_role=spec.slot1_source.role if spec.slot1_source else None,
                slot2_source_matchup_id=spec.slot2_source.matchup_id if spec.slot2_source else None,
                slot2_source_role=spec.slot2_source.role if spec.slot2_source else None,
            )
            for spec in specs
        ]

        seeds = self._derive_seeds(specs)
        for entrant in entrants:
            entrant.seed = seeds.get(entrant.agent_id)

        tournament.status = TournamentStatus.RUNNING
        tournament.updated_at = now
        self._repository.save_all([*matchups, *entrants, tournament])

        logger.info("Tournament %s started with %d entrants, %d matchups", tournament.id, len(entrants), len(matchups))

        # Queue round 1 immediately; subsequent polls keep it advancing.
        await self.advance_tournament(tournament)
        return tournament

    def cancel_tournament(self, tournament_id: UUID) -> Tournament:
        """Cancel a tournament; already-running matches finish but are ignored."""
        tournament = self._repository.get_by_id(tournament_id)
        if not tournament:
            raise TournamentNotFoundError("Tournament not found")
        if tournament.status in (TournamentStatus.COMPLETED, TournamentStatus.CANCELLED):
            raise TournamentStateError(f"Tournament cannot be cancelled from status '{tournament.status.value}'")

        now = datetime.now(UTC)
        to_save: list[Any] = []
        for matchup in self._repository.list_matchups(tournament_id):
            if matchup.status not in _TERMINAL_MATCHUP_STATUSES:
                matchup.status = MatchupStatus.CANCELLED
                matchup.updated_at = now
                to_save.append(matchup)

        tournament.status = TournamentStatus.CANCELLED
        tournament.updated_at = now
        to_save.append(tournament)
        self._repository.save_all(to_save)

        logger.info("Tournament %s cancelled", tournament.id)
        return tournament

    def resolve_matchup(self, tournament_id: UUID, matchup_id: UUID, winner_agent_id: UUID) -> TournamentMatchup:
        """
        Admin resolution for a matchup flagged NEEDS_ATTENTION (e.g. repeated
        infrastructure failures): record the winner so the bracket can advance.
        """
        tournament = self._repository.get_by_id(tournament_id)
        if not tournament:
            raise TournamentNotFoundError("Tournament not found")

        matchup = self._repository.get_matchup(matchup_id)
        if not matchup or matchup.tournament_id != tournament_id:
            raise TournamentNotFoundError("Matchup not found in this tournament")
        if matchup.status != MatchupStatus.NEEDS_ATTENTION:
            raise TournamentStateError(f"Matchup cannot be resolved from status '{matchup.status.value}'")
        if winner_agent_id not in (matchup.agent1_id, matchup.agent2_id):
            raise TournamentServiceError("winner_agent_id must be one of the matchup participants")

        now = datetime.now(UTC)
        matchup.winner_agent_id = winner_agent_id
        matchup.status = MatchupStatus.COMPLETED
        matchup.updated_at = now
        matchup = self._repository.save_matchup(matchup)

        # Clear the tournament-level flag if no other matchups need attention.
        remaining = [
            m for m in self._repository.list_matchups(tournament_id) if m.status == MatchupStatus.NEEDS_ATTENTION
        ]
        if tournament.status == TournamentStatus.NEEDS_ATTENTION and not remaining:
            tournament.status = TournamentStatus.RUNNING
            tournament.updated_at = now
            self._repository.save(tournament)

        logger.info(
            "Matchup %s of tournament %s resolved by admin: winner %s", matchup.id, tournament_id, winner_agent_id
        )
        return matchup

    # --- Advancement engine (called by the tournament scheduler) ---

    async def advance_tournament(self, tournament: Tournament) -> None:
        """
        One idempotent advancement pass, re-deriving all state from the DB:
        records finished games (best-of-3 / coin-flip / forfeit rules), retries
        infrastructure failures, completes matchups, opens the next stage once
        the current one is fully terminal, and detects tournament completion.
        """
        if tournament.status not in (TournamentStatus.RUNNING, TournamentStatus.NEEDS_ATTENTION):
            return

        config = TournamentConfig(**(tournament.config or {}))
        matchups = list(self._repository.list_matchups(tournament.id))
        matchups_by_id = {matchup.id: matchup for matchup in matchups}

        games_by_matchup: dict[UUID, list[TournamentGame]] = {}
        for game in self._repository.list_games(tournament.id):
            games_by_matchup.setdefault(game.matchup_id, []).append(game)

        match_ids = [game.match_id for games in games_by_matchup.values() for game in games if game.match_id]
        matches_by_id = {match.id: match for match in self._match_repository.list_by_ids(match_ids)}

        active = self._match_repository.count_active_by_tournament(tournament.id)
        capacity = max(0, config.max_concurrent_matches - active)

        # 1. Progress matchups that already have games running.
        for matchup in matchups:
            if matchup.status == MatchupStatus.IN_PROGRESS:
                capacity = await self._progress_matchup(
                    tournament, config, matchup, games_by_matchup.get(matchup.id, []), matches_by_id, capacity
                )

        # 2. Round-by-round gate: open the lowest non-terminal stage.
        open_matchups = [m for m in matchups if m.status not in _TERMINAL_MATCHUP_STATUSES]
        if not open_matchups:
            self._complete_tournament(tournament, matchups)
            return

        current_stage = min(matchup.stage for matchup in open_matchups)
        for matchup in open_matchups:
            if matchup.stage == current_stage and matchup.status == MatchupStatus.PENDING:
                capacity = await self._open_matchup(tournament, config, matchup, matchups_by_id, capacity)

        self._sync_tournament_attention_flag(tournament, matchups)

    # --- Internals ---

    def _validate_config(self, game_type: GameType, config: TournamentConfig) -> None:
        if config.turn_time_limit <= 0 or config.turn_time_limit > settings.MAX_TURN_TIME_LIMIT_SECONDS:
            raise TournamentServiceError(
                f"turn_time_limit must be between 0.1 and {settings.MAX_TURN_TIME_LIMIT_SECONDS}s"
            )
        if not (1 <= config.max_concurrent_matches <= self.MAX_CONCURRENT_HARD_CAP):
            raise TournamentServiceError(f"max_concurrent_matches must be between 1 and {self.MAX_CONCURRENT_HARD_CAP}")
        try:
            validate_state_init_data(game_type, config.state_init_data)
        except StateInitValidationError as e:
            raise TournamentServiceError(str(e)) from e

    def _validate_entrants_per_arena(self, arena_id: UUID, game_type: GameType, agent_ids: list[UUID]) -> None:
        if len(agent_ids) < self.MIN_ENTRANTS:
            raise TournamentServiceError(f"A tournament requires at least {self.MIN_ENTRANTS} entrants")
        if len(agent_ids) > settings.MAX_TOURNAMENT_ENTRANTS:
            raise TournamentServiceError(f"A tournament allows at most {settings.MAX_TOURNAMENT_ENTRANTS} entrants")
        if len(set(agent_ids)) != len(agent_ids):
            raise TournamentServiceError("Duplicate agents are not allowed")

        agents = self._agent_repository.list_by_ids(agent_ids)
        agents_by_id = {agent.id: agent for agent in agents}
        for agent_id in agent_ids:
            agent = agents_by_id.get(agent_id)
            if agent is None:
                raise TournamentServiceError(f"Agent {agent_id} was not found")
            if agent.arena_id != arena_id:
                raise TournamentServiceError(f"Agent {agent.id} does not belong to target arena")
            if agent.game_type != game_type:
                raise TournamentServiceError(f"Agent {agent.id} does not belong to game '{game_type}'")
            if agent.active_submission is None or not submission_has_successful_build(agent.active_submission):
                raise TournamentServiceError(f"Agent {agent.id} does not have a successful active submission")

    @staticmethod
    def _derive_seeds(specs: list[MatchupSpec]) -> dict[UUID, int]:
        """Seed numbers in bracket order, read off the generated round-1 placement."""
        seeds: dict[UUID, int] = {}
        round_one = sorted(
            (s for s in specs if s.bracket == BracketSide.WINNERS and s.round == 1), key=lambda s: s.position
        )
        seed = 1
        for spec in round_one:
            for agent_id in (spec.agent1_id, spec.agent2_id):
                if agent_id is not None:
                    seeds[agent_id] = seed
                    seed += 1
        return seeds

    async def _progress_matchup(
        self,
        tournament: Tournament,
        config: TournamentConfig,
        matchup: TournamentMatchup,
        games: list[TournamentGame],
        matches_by_id: dict[UUID, Match],
        capacity: int,
    ) -> int:
        """Record finished games, retry failures, decide the best-of-3, queue the next game."""
        games = sorted(games, key=lambda g: g.game_index)

        for game in games:
            if game.winner_agent_id is not None:
                continue
            capacity = await self._process_unresolved_game(tournament, config, matchup, game, matches_by_id, capacity)
            if matchup.status == MatchupStatus.NEEDS_ATTENTION:
                break

        if matchup.status != MatchupStatus.IN_PROGRESS:
            return capacity

        # Catch up the second parallel game if the cap was full when the matchup
        # opened, then decide the matchup / queue the decider.
        capacity = await self._ensure_first_two_games(tournament, config, matchup, games, capacity)
        return await self._decide_matchup(tournament, config, matchup, games, capacity)

    async def _process_unresolved_game(
        self,
        tournament: Tournament,
        config: TournamentConfig,
        matchup: TournamentMatchup,
        game: TournamentGame,
        matches_by_id: dict[UUID, Match],
        capacity: int,
    ) -> int:
        if game.match_id is None:
            # Scheduler crashed (or capacity was full) between creating the
            # game row and its match — queue the match now.
            if capacity > 0 and await self._queue_match_for_game(tournament, config, matchup, game):
                capacity -= 1
            return capacity

        match = matches_by_id.get(game.match_id)
        if match is None:
            logger.error("Tournament game %s references missing match %s", game.id, game.match_id)
            self._flag_needs_attention(matchup)
            return capacity
        if match.status not in _TERMINAL_MATCH_STATUSES:
            return capacity  # still queued/running

        if match.status == MatchStatus.COMPLETED:
            return await self._resolve_completed_game(tournament, config, matchup, game, match, capacity)
        if match.status == MatchStatus.CLIENT_ERROR:
            self._resolve_client_error_game(matchup, game, match)
            return capacity
        # MatchStatus.FAILED — infrastructure failure, not an agent's fault
        return await self._retry_or_flag_game(tournament, config, matchup, game, capacity)

    async def _resolve_completed_game(
        self,
        tournament: Tournament,
        config: TournamentConfig,
        matchup: TournamentMatchup,
        game: TournamentGame,
        match: Match,
        capacity: int,
    ) -> int:
        winner = self._parse_result_winner(match, matchup)
        if winner == "draw":
            order = game_agent_order(matchup.id, *self._participants(matchup), game.game_index)
            game.winner_agent_id = deterministic_coin_flip(matchup.id, game.game_index, order[0], order[1])
            game.resolution = GameResolution.DRAW_COIN_FLIP
            self._save_game(game)
            logger.info("Tournament game %s drew; coin flip awarded it to agent %s", game.id, game.winner_agent_id)
        elif isinstance(winner, UUID):
            game.winner_agent_id = winner
            game.resolution = GameResolution.PLAYED
            self._save_game(game)
        else:
            # Completed without a usable winner — treat like an infrastructure failure.
            logger.warning("Tournament game %s completed without a usable winner; retrying", game.id)
            capacity = await self._retry_or_flag_game(tournament, config, matchup, game, capacity)
        return capacity

    def _resolve_client_error_game(self, matchup: TournamentMatchup, game: TournamentGame, match: Match) -> None:
        """An agent's own code erred: that agent forfeits the game (the worker names the other agent winner)."""
        winner = self._parse_result_winner(match, matchup)
        if isinstance(winner, UUID):
            game.winner_agent_id = winner
            game.resolution = GameResolution.FORFEIT_CLIENT_ERROR
            self._save_game(game)
            logger.info("Tournament game %s forfeited via client error; winner %s", game.id, winner)
        else:
            # Cannot attribute the error to one agent — fail safe to admin review.
            logger.warning("Tournament game %s ended in client error without attribution", game.id)
            self._flag_needs_attention(matchup)

    async def _retry_or_flag_game(
        self,
        tournament: Tournament,
        config: TournamentConfig,
        matchup: TournamentMatchup,
        game: TournamentGame,
        capacity: int,
    ) -> int:
        if game.retry_count >= settings.TOURNAMENT_MAX_GAME_RETRIES:
            logger.warning(
                "Tournament game %s exhausted %d retries; matchup %s needs admin attention",
                game.id,
                game.retry_count,
                matchup.id,
            )
            self._flag_needs_attention(matchup)
            return capacity

        game.retry_count += 1
        game.match_id = None
        self._save_game(game)
        logger.info("Re-queueing failed tournament game %s (retry %d)", game.id, game.retry_count)
        if capacity > 0 and await self._queue_match_for_game(tournament, config, matchup, game):
            capacity -= 1
        return capacity

    async def _decide_matchup(
        self,
        tournament: Tournament,
        config: TournamentConfig,
        matchup: TournamentMatchup,
        games: list[TournamentGame],
        capacity: int,
    ) -> int:
        wins: dict[UUID, int] = {}
        for game in games:
            if game.winner_agent_id is not None:
                wins[game.winner_agent_id] = wins.get(game.winner_agent_id, 0) + 1

        for agent_id, win_count in wins.items():
            if win_count >= GAMES_TO_WIN_MATCHUP:
                matchup.winner_agent_id = agent_id
                matchup.status = MatchupStatus.COMPLETED
                matchup.updated_at = datetime.now(UTC)
                self._repository.save_matchup(matchup)
                logger.info("Matchup %s completed; winner %s", matchup.id, agent_id)
                return capacity

        # No 2-0 yet: a decider is only needed once both parallel games are
        # resolved and split 1-1 (each side won one).
        by_index = {game.game_index: game for game in games}
        first, second = by_index.get(0), by_index.get(1)
        tied_one_one = (
            first is not None
            and second is not None
            and first.winner_agent_id is not None
            and second.winner_agent_id is not None
            and first.winner_agent_id != second.winner_agent_id
        )
        if (
            tied_one_one
            and DECIDER_GAME_INDEX not in by_index
            and capacity > 0
            and await self._create_game(tournament, config, matchup, DECIDER_GAME_INDEX)
        ):
            capacity -= 1
        return capacity

    async def _open_matchup(
        self,
        tournament: Tournament,
        config: TournamentConfig,
        matchup: TournamentMatchup,
        matchups_by_id: dict[UUID, TournamentMatchup],
        capacity: int,
    ) -> int:
        """Fill a pending matchup's slots; auto-complete byes; queue games 1 and 2."""
        now = datetime.now(UTC)

        if matchup.bracket == BracketSide.GRAND_FINAL_RESET:
            grand_final = (
                matchups_by_id.get(matchup.slot1_source_matchup_id) if matchup.slot1_source_matchup_id else None
            )
            # No reset needed when the winners-bracket champion (slot 1 of the
            # grand final) defends the grand final.
            if grand_final is None or grand_final.winner_agent_id == grand_final.agent1_id:
                matchup.status = MatchupStatus.CANCELLED
                matchup.updated_at = now
                self._repository.save_matchup(matchup)
                return capacity

        matchup.agent1_id = self._resolve_slot(
            matchup.agent1_id, matchup.slot1_source_matchup_id, matchup.slot1_source_role, matchups_by_id
        )
        matchup.agent2_id = self._resolve_slot(
            matchup.agent2_id, matchup.slot2_source_matchup_id, matchup.slot2_source_role, matchups_by_id
        )

        if matchup.agent1_id is None and matchup.agent2_id is None:
            # Both feeders were byes; nobody advances from here.
            matchup.status = MatchupStatus.COMPLETED
            matchup.updated_at = now
            self._repository.save_matchup(matchup)
            return capacity

        if matchup.agent1_id is None or matchup.agent2_id is None:
            # Bye: the present agent advances without playing.
            matchup.winner_agent_id = matchup.agent1_id or matchup.agent2_id
            matchup.status = MatchupStatus.COMPLETED
            matchup.updated_at = now
            self._repository.save_matchup(matchup)
            return capacity

        matchup.updated_at = now
        self._repository.save_matchup(matchup)

        # Queue both games of the best-of-3 so they can run in parallel; the
        # decider (game 3) is created later, only if the matchup ends up 1-1.
        return await self._ensure_first_two_games(tournament, config, matchup, [], capacity)

    async def _ensure_first_two_games(
        self,
        tournament: Tournament,
        config: TournamentConfig,
        matchup: TournamentMatchup,
        games: list[TournamentGame],
        capacity: int,
    ) -> int:
        """
        Create the matchup's first two games (up to the concurrency cap).

        Games 1 and 2 have fixed, result-independent agent orders, so they may
        run simultaneously. When the cap can only fit one right now, the other is
        created on a later poll; creation is idempotent since each index is only
        created once.
        """
        existing = {game.game_index for game in games}
        for game_index in PARALLEL_GAME_INDICES:
            if capacity <= 0:
                break
            if game_index in existing:
                continue
            if await self._create_game(tournament, config, matchup, game_index):
                capacity -= 1
        return capacity

    @staticmethod
    def _resolve_slot(
        current: UUID | None,
        source_matchup_id: UUID | None,
        source_role: SlotSourceRole | None,
        matchups_by_id: dict[UUID, TournamentMatchup],
    ) -> UUID | None:
        if current is not None:
            return current
        if source_matchup_id is None:
            return None  # fixed entrant slot that was seeded as a bye
        source = matchups_by_id.get(source_matchup_id)
        if source is None:
            return None
        if source_role == SlotSourceRole.WINNER:
            return source.winner_agent_id
        # Loser slot: a bye matchup (or double bye) produces no loser.
        if source.winner_agent_id is None:
            return None
        return source.agent2_id if source.winner_agent_id == source.agent1_id else source.agent1_id

    async def _create_game(
        self,
        tournament: Tournament,
        config: TournamentConfig,
        matchup: TournamentMatchup,
        game_index: int,
    ) -> bool:
        """Create the game row first, then its match, so a crash in between is recoverable."""
        game = TournamentGame(
            tournament_id=tournament.id,
            matchup_id=matchup.id,
            game_index=game_index,
        )
        self._repository.save_game(game)

        if matchup.status != MatchupStatus.IN_PROGRESS:
            matchup.status = MatchupStatus.IN_PROGRESS
            matchup.updated_at = datetime.now(UTC)
            self._repository.save_matchup(matchup)

        return await self._queue_match_for_game(tournament, config, matchup, game)

    async def _queue_match_for_game(
        self,
        tournament: Tournament,
        config: TournamentConfig,
        matchup: TournamentMatchup,
        game: TournamentGame,
    ) -> bool:
        """Create and enqueue the Match backing a game; returns True if one was queued."""
        agent_ids = game_agent_order(matchup.id, *self._participants(matchup), game.game_index)
        match_config = MatchConfig(
            turn_time_limit=config.turn_time_limit,
            state_init_data=dict(config.state_init_data),
        )
        try:
            match = await self._match_service.create_match(
                arena_id=tournament.arena_id,
                config=match_config,
                agent_ids=agent_ids,
                tournament_id=tournament.id,
            )
        except MatchServiceError:
            # Permanent validation failure (e.g. an agent lost its successful
            # submission mid-tournament) — needs an admin decision.
            logger.exception("Failed to create match for tournament game %s", game.id)
            self._flag_needs_attention(matchup)
            return False
        except Exception:
            # Transient failure (e.g. queue unavailable); the next poll retries.
            logger.exception("Transient error queueing match for tournament game %s", game.id)
            return False

        game.match_id = match.id
        self._save_game(game)
        logger.info(
            "Queued tournament match %s (matchup %s, game %d, agents %s)",
            match.id,
            matchup.id,
            game.game_index,
            agent_ids,
        )
        return True

    def _flag_needs_attention(self, matchup: TournamentMatchup) -> None:
        if matchup.status != MatchupStatus.NEEDS_ATTENTION:
            matchup.status = MatchupStatus.NEEDS_ATTENTION
            matchup.updated_at = datetime.now(UTC)
            self._repository.save_matchup(matchup)

    def _sync_tournament_attention_flag(self, tournament: Tournament, matchups: list[TournamentMatchup]) -> None:
        needs_attention = any(matchup.status == MatchupStatus.NEEDS_ATTENTION for matchup in matchups)
        new_status = TournamentStatus.NEEDS_ATTENTION if needs_attention else TournamentStatus.RUNNING
        if tournament.status != new_status:
            tournament.status = new_status
            tournament.updated_at = datetime.now(UTC)
            self._repository.save(tournament)

    def _complete_tournament(self, tournament: Tournament, matchups: list[TournamentMatchup]) -> None:
        grand_final = next((m for m in matchups if m.bracket == BracketSide.GRAND_FINAL), None)
        reset = next((m for m in matchups if m.bracket == BracketSide.GRAND_FINAL_RESET), None)

        champion: UUID | None = None
        if reset is not None and reset.status == MatchupStatus.COMPLETED:
            champion = reset.winner_agent_id
        elif grand_final is not None:
            champion = grand_final.winner_agent_id

        tournament.status = TournamentStatus.COMPLETED
        tournament.winner_agent_id = champion
        tournament.updated_at = datetime.now(UTC)
        self._repository.save(tournament)
        logger.info("Tournament %s completed; champion %s", tournament.id, champion)

    @staticmethod
    def _participants(matchup: TournamentMatchup) -> tuple[UUID, UUID]:
        """Both agents of a matchup that is being played; an empty slot here is an invariant violation."""
        if matchup.agent1_id is None or matchup.agent2_id is None:
            raise TournamentServiceError(f"Matchup {matchup.id} is missing a participant")
        return matchup.agent1_id, matchup.agent2_id

    @staticmethod
    def _parse_result_winner(match: Match, matchup: TournamentMatchup) -> UUID | str | None:
        """Winner from an untrusted worker result: a participant UUID, 'draw', or None."""
        result = match.result or {}
        winner = result.get("winner")
        if winner == "draw":
            return "draw"
        try:
            winner_id = UUID(str(winner))
        except (ValueError, TypeError):
            return None
        if winner_id in (matchup.agent1_id, matchup.agent2_id):
            return winner_id
        return None

    def _save_game(self, game: TournamentGame) -> None:
        game.updated_at = datetime.now(UTC)
        self._repository.save_game(game)

    def _compute_standings(
        self,
        tournament: Tournament,
        entrants: Sequence[TournamentEntrant],
        matchups: Sequence[TournamentMatchup],
        agent_names: dict[UUID, str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Placement-ordered standings. An entrant is eliminated when they lose in
        the losers bracket, lose the grand final coming from the losers side,
        or lose the grand-final reset; later eliminations place higher.
        """
        wins: dict[UUID, int] = {}
        losses: dict[UUID, int] = {}
        eliminated: dict[UUID, TournamentMatchup] = {}

        for matchup in matchups:
            if matchup.status != MatchupStatus.COMPLETED or matchup.winner_agent_id is None:
                continue
            if matchup.agent1_id is None or matchup.agent2_id is None:
                continue  # byes are not played
            winner = matchup.winner_agent_id
            loser = matchup.agent2_id if winner == matchup.agent1_id else matchup.agent1_id
            wins[winner] = wins.get(winner, 0) + 1
            losses[loser] = losses.get(loser, 0) + 1

            is_elimination = matchup.bracket in (BracketSide.LOSERS, BracketSide.GRAND_FINAL_RESET) or (
                matchup.bracket == BracketSide.GRAND_FINAL and loser == matchup.agent2_id
            )
            if is_elimination:
                eliminated[loser] = matchup

        champion = tournament.winner_agent_id if tournament.status == TournamentStatus.COMPLETED else None

        # Later stages place higher; entrants eliminated at the same stage tie.
        placements: dict[UUID, int] = {}
        if champion is not None:
            placements[champion] = 1
        placed = len(placements)
        for stage in sorted({m.stage for m in eliminated.values()}, reverse=True):
            group = [agent_id for agent_id, m in eliminated.items() if m.stage == stage]
            for agent_id in group:
                placements[agent_id] = placed + 1
            placed += len(group)

        standings = [
            {
                "agent_id": entrant.agent_id,
                "agent_name": (agent_names or {}).get(entrant.agent_id),
                "seed": entrant.seed,
                "placement": placements.get(entrant.agent_id),
                "matchup_wins": wins.get(entrant.agent_id, 0),
                "matchup_losses": losses.get(entrant.agent_id, 0),
                "eliminated_in_bracket": eliminated[entrant.agent_id].bracket
                if entrant.agent_id in eliminated
                else None,
                "eliminated_in_round": eliminated[entrant.agent_id].round if entrant.agent_id in eliminated else None,
            }
            for entrant in entrants
        ]
        # Placed entrants first (best placement on top), then entrants still in the running.
        standings.sort(key=lambda s: (s["placement"] is None, s["placement"] or 0))
        return standings

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlmodel import JSON, Column, Field, SQLModel

from app.models.game import GameType


class TournamentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NEEDS_ATTENTION = "needs_attention"


class BracketSide(str, Enum):
    """Which bracket a matchup belongs to in the double-elimination tree."""

    WINNERS = "winners"
    LOSERS = "losers"
    GRAND_FINAL = "grand_final"
    GRAND_FINAL_RESET = "grand_final_reset"


class MatchupStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NEEDS_ATTENTION = "needs_attention"
    CANCELLED = "cancelled"


class SlotSourceRole(str, Enum):
    """Whether a matchup slot is fed by the winner or the loser of its source matchup."""

    WINNER = "winner"
    LOSER = "loser"


class GameResolution(str, Enum):
    """How a best-of-3 game's winner was determined."""

    PLAYED = "played"
    DRAW_COIN_FLIP = "draw_coin_flip"
    FORFEIT_CLIENT_ERROR = "forfeit_client_error"
    ADMIN_RESOLVED = "admin_resolved"


class TournamentConfig(BaseModel):
    """
    Typed configuration for a tournament.

    Serialised as JSON in the ``config`` column; extend this model to add
    new per-tournament settings without touching the DB schema.
    """

    turn_time_limit: float = 10.0
    max_concurrent_matches: int = 64
    state_init_data: dict[str, Any] = {}


class Tournament(SQLModel, table=True):
    """
    Represents a double-elimination tournament between agents of one game type.
    """

    __tablename__ = "tournaments"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)

    name: str = Field(nullable=False)

    game_type: GameType = Field(nullable=False, index=True)

    status: TournamentStatus = Field(default=TournamentStatus.PENDING, nullable=False, index=True)

    # Configuration for the tournament (turn time limit, concurrency cap, game init data)
    config: dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Champion agent, set when the tournament completes
    winner_agent_id: UUID | None = Field(default=None, nullable=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)


class TournamentEntrant(SQLModel, table=True):
    """
    An agent participating in a tournament. The seed is assigned (randomly)
    when the tournament is started.
    """

    __tablename__ = "tournament_entrants"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)

    tournament_id: UUID = Field(foreign_key="tournaments.id", index=True, nullable=False)
    agent_id: UUID = Field(index=True, nullable=False)

    seed: int | None = Field(default=None, nullable=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)


class TournamentMatchup(SQLModel, table=True):
    """
    A best-of-3 matchup between two bracket slots.

    Slots are either fixed entrants (set at seeding time) or fed by the
    winner/loser of a source matchup (resolved by the tournament scheduler
    once the source completes). A slot that resolves to no agent is a bye:
    the matchup auto-completes in favour of the present agent.

    ``stage`` is a global ordering index across both brackets: a matchup may
    only be filled and queued once every matchup with a lower stage is in a
    terminal state (round-by-round scheduling).
    """

    __tablename__ = "tournament_matchups"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)

    tournament_id: UUID = Field(foreign_key="tournaments.id", index=True, nullable=False)

    bracket: BracketSide = Field(nullable=False)
    # 1-based round within the bracket side
    round: int = Field(nullable=False)
    # 0-based position within the round, used to wire source links
    position: int = Field(nullable=False)
    # Global round-gating index across both brackets
    stage: int = Field(nullable=False, index=True)

    # Participants; None = not yet filled, or a bye once the matchup is terminal
    agent1_id: UUID | None = Field(default=None, nullable=True)
    agent2_id: UUID | None = Field(default=None, nullable=True)

    # Where each slot's participant comes from (None = fixed entrant slot)
    slot1_source_matchup_id: UUID | None = Field(default=None, nullable=True)
    slot1_source_role: SlotSourceRole | None = Field(default=None, nullable=True)
    slot2_source_matchup_id: UUID | None = Field(default=None, nullable=True)
    slot2_source_role: SlotSourceRole | None = Field(default=None, nullable=True)

    status: MatchupStatus = Field(default=MatchupStatus.PENDING, nullable=False, index=True)

    # Winner of the best-of-3 (None until decided; stays None for a double-bye)
    winner_agent_id: UUID | None = Field(default=None, nullable=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)


class TournamentGame(SQLModel, table=True):
    """
    A single game of a best-of-3 matchup, backed by a real Match.

    The game row is created before its Match so a crashed scheduler can
    resume: a game with ``match_id`` None is (re-)queued on the next poll.
    Retries after infrastructure failures replace ``match_id`` and bump
    ``retry_count``.
    """

    __tablename__ = "tournament_games"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)

    tournament_id: UUID = Field(foreign_key="tournaments.id", index=True, nullable=False)
    matchup_id: UUID = Field(foreign_key="tournament_matchups.id", index=True, nullable=False)

    # 0-based index within the best-of-3; even games start with agent1, odd with agent2
    game_index: int = Field(nullable=False)

    # The current Match backing this game (None while creation is pending)
    match_id: UUID | None = Field(default=None, nullable=True, index=True)

    retry_count: int = Field(default=0, nullable=False)

    winner_agent_id: UUID | None = Field(default=None, nullable=True)
    resolution: GameResolution | None = Field(default=None, nullable=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

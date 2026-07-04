from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.game import GameType
from app.models.tournament import (
    BracketSide,
    GameResolution,
    MatchupStatus,
    SlotSourceRole,
    TournamentConfig,
    TournamentStatus,
)


class TournamentBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    game_type: GameType | None = None
    arena_id: UUID
    config: TournamentConfig = Field(default_factory=TournamentConfig)


class TournamentCreate(TournamentBase):
    """Admin-curated tournament creation: explicit list of participating agents."""

    agent_ids: list[UUID] = Field(min_length=2, max_length=512)


class TournamentRead(TournamentBase):
    id: UUID
    status: TournamentStatus
    winner_agent_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("config", mode="before")
    @classmethod
    def coerce_config(cls, v: Any) -> TournamentConfig:
        """Accept a raw dict from the DB and coerce it into a TournamentConfig."""
        if isinstance(v, dict):
            return TournamentConfig(**v)
        return v


class TournamentEntrantRead(BaseModel):
    agent_id: UUID
    seed: int | None
    agent_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TournamentGameRead(BaseModel):
    id: UUID
    game_index: int
    match_id: UUID | None
    retry_count: int
    winner_agent_id: UUID | None
    resolution: GameResolution | None

    model_config = ConfigDict(from_attributes=True)


class TournamentMatchupRead(BaseModel):
    id: UUID
    bracket: BracketSide
    round: int
    position: int
    stage: int
    agent1_id: UUID | None
    agent2_id: UUID | None
    # Bracket wiring, so clients can draw connector lines between matchups
    slot1_source_matchup_id: UUID | None
    slot1_source_role: SlotSourceRole | None
    slot2_source_matchup_id: UUID | None
    slot2_source_role: SlotSourceRole | None
    status: MatchupStatus
    winner_agent_id: UUID | None
    games: list[TournamentGameRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TournamentStandingRead(BaseModel):
    agent_id: UUID
    agent_name: str | None = None
    seed: int | None
    placement: int | None
    matchup_wins: int
    matchup_losses: int
    eliminated_in_bracket: BracketSide | None
    eliminated_in_round: int | None


class TournamentBracketRead(BaseModel):
    """Full bracket view: tournament, entrants, matchups with their games, standings."""

    tournament: TournamentRead
    entrants: list[TournamentEntrantRead]
    matchups: list[TournamentMatchupRead]
    standings: list[TournamentStandingRead]


class MatchupResolveRequest(BaseModel):
    """Admin request to resolve a stuck (NEEDS_ATTENTION) matchup."""

    winner_agent_id: UUID

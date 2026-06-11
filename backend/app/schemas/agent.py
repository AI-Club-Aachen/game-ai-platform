from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.game import GameType


class AgentBase(BaseModel):
    name: str
    game_type: GameType


class AgentCreate(AgentBase):
    user_id: UUID
    active_submission_id: UUID | None = None


class AgentUpdate(BaseModel):
    """
    User-facing update payload. Stats (wins/losses/draws/matches_played/elo)
    are intentionally NOT updatable here; they change only via the internal
    match-completion path. Unknown fields are rejected so stat writes fail loudly.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    active_submission_id: UUID | None = None


class AgentRead(AgentBase):
    id: UUID
    user_id: UUID
    active_submission_id: UUID | None
    wins: int
    losses: int
    draws: int
    matches_played: int
    elo: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

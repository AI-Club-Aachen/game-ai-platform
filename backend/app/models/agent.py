from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from app.models.game import GameType


if TYPE_CHECKING:
    from app.models.submission import Submission


class Agent(SQLModel, table=True):
    """
    Represents an agent of a user that can participate in a match.
    """

    __tablename__ = "agents"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)

    user_id: UUID = Field(index=True, nullable=False)

    game_type: GameType = Field(nullable=False, index=True)

    active_submission_id: UUID | None = Field(
        default=None,
        foreign_key="submissions.id",
        nullable=True,
    )
    active_submission: Optional["Submission"] = Relationship(back_populates="agents")

    stats: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # TODO: change from freeform json

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

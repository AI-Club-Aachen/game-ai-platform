from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from app.models.game import GameType

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.match import Match
    from app.models.submission import Submission
    from app.models.tournament import Tournament


class Arena(SQLModel, table=True):
    """
    Represents an Arena that belongs to a Game type and has a custom configuration.
    """

    __tablename__ = "arenas"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    name: str = Field(nullable=False)
    description: Optional[str] = Field(default=None, nullable=True)

    # Reference to the game type being played (tictactoe, hex, connect_four, chess)
    game_type: GameType = Field(nullable=False, index=True)

    # Custom configuration for the arena (board_size, turn_time_limit, rules)
    config: dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Password for simple authentication/access protection
    password: Optional[str] = Field(default=None, nullable=True)

    is_active: bool = Field(default=True, nullable=False)

    # Relationships
    agents: list["Agent"] = Relationship(
        back_populates="arena",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    submissions: list["Submission"] = Relationship(
        back_populates="arena",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    matches: list["Match"] = Relationship(
        back_populates="arena",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    tournaments: list["Tournament"] = Relationship(
        back_populates="arena",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    @property
    def has_password(self) -> bool:
        return self.password is not None and self.password != ""

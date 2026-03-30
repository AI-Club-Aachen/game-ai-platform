from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.job import BuildJob


class Submission(SQLModel, table=True):
    """
    Represents an uploaded agent submission.
    Tracks the build status and resulting Docker image.
    """

    __tablename__ = "submissions"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    user_id: UUID = Field(index=True, nullable=False)  # Foreign key to User, but loose coupling for now

    # Path to the uploaded zip file
    object_path: str = Field(nullable=False)

    build_jobs: list["BuildJob"] = Relationship(
        back_populates="submission",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    agents: list["Agent"] = Relationship(back_populates="active_submission")

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

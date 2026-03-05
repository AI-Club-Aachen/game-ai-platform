from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field, Relationship, SQLModel


if TYPE_CHECKING:
    from app.models.submission import Submission


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BuildJob(SQLModel, table=True):
    """
    Represents a background job to build a submission (Docker image).
    """
    __tablename__ = "build_jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    submission_id: UUID = Field(foreign_key="submissions.id", index=True, nullable=False)

    submission: Optional["Submission"] = Relationship(back_populates="build_jobs")

    status: JobStatus = Field(default=JobStatus.QUEUED, nullable=False)

    # Logs from the build process
    logs: str = Field(default="")

    # Resulting Docker Image ID and Tag
    image_id: str | None = Field(default=None, nullable=True)
    image_tag: str | None = Field(default=None, nullable=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)


class MatchJob(SQLModel, table=True):
    """
    Represents a background job to execute a match.
    """
    __tablename__ = "match_jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    match_id: UUID = Field(index=True, nullable=False)

    status: JobStatus = Field(default=JobStatus.QUEUED, nullable=False)

    # Logs from the match execution
    logs: str = Field(default="")

    # Result of the match (scores, winner, etc.)
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

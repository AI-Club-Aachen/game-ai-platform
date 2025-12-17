from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class SubmissionStatus(str, Enum):
    QUEUED = "queued"
    BUILDING = "building"
    COMPLETED = "completed"
    FAILED = "failed"


class Submission(SQLModel, table=True):
    """
    Represents an uploaded agent submission.
    Tracks the build status and resulting Docker image.
    """

    __tablename__ = "submissions"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, nullable=False)
    user_id: UUID = Field(index=True, nullable=False)  # Foreign key to User, but loose coupling for now
    
    status: SubmissionStatus = Field(default=SubmissionStatus.QUEUED, nullable=False)
    
    # Path to the uploaded zip file
    object_path: str = Field(nullable=False)
    
    # Docker Image ID
    image_id: str | None = Field(default=None, nullable=True)
    
    # Docker Image Tag
    image_tag: str | None = Field(default=None, nullable=True)
    
    # Build logs or error message
    logs: str | None = Field(default=None, nullable=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

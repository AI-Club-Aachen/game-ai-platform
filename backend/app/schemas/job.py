from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.job import JobStatus


class BuildJobUpdate(BaseModel):
    """Schema for updating a build job (used by workers)."""
    status: JobStatus
    logs: str | None = None
    image_id: str | None = None
    image_tag: str | None = None


class BuildJobRead(BaseModel):
    id: UUID
    submission_id: UUID
    status: JobStatus
    logs: str | None
    image_id: str | None
    image_tag: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatchJobUpdate(BaseModel):
    """Schema for updating a match job (used by workers)."""
    status: JobStatus
    logs: str | None = None
    result: dict[str, Any] | None = None


class MatchJobRead(BaseModel):
    id: UUID
    match_id: UUID
    status: JobStatus
    logs: str | None
    result: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

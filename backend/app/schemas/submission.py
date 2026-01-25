from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.submission import SubmissionStatus


class SubmissionBase(BaseModel):
    pass


class SubmissionCreate(SubmissionBase):
    pass  # We don't take JSON body for create, likely just a file upload


class SubmissionUpdate(BaseModel):
    """Schema for updating a submission (used by workers)."""
    status: SubmissionStatus
    logs: str | None = None
    image_id: str | None = None
    image_tag: str | None = None


class SubmissionRead(SubmissionBase):
    id: UUID
    user_id: UUID
    status: SubmissionStatus
    image_id: str | None
    image_tag: str | None
    logs: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

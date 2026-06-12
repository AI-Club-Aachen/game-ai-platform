from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubmissionFreezeRead(BaseModel):
    enabled: bool
    updated_at: datetime
    updated_by_user_id: UUID | None

    model_config = ConfigDict(from_attributes=True)


class SubmissionFreezeUpdate(BaseModel):
    enabled: bool

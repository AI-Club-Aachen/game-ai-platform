from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.game import GameType
from app.schemas.job import BuildJobRead


class SubmissionBase(BaseModel):
    pass


class SubmissionCreate(SubmissionBase):
    pass  # We don't take JSON body for create, likely just a file upload


class SubmissionRead(SubmissionBase):
    id: UUID
    user_id: UUID
    name: str
    game_type: GameType
    created_at: datetime
    updated_at: datetime
    build_jobs: list[BuildJobRead] = []

    model_config = ConfigDict(from_attributes=True)

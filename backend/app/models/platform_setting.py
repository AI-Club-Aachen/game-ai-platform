from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class PlatformSetting(SQLModel, table=True):
    """
    An admin override of an editable ``Settings`` value (see app/core/runtime_settings.py).

    Rows are applied on top of the environment at startup and whenever an admin
    saves the settings page; deleting a row restores the environment/default value.
    """

    __tablename__ = "platform_settings"

    name: str = Field(primary_key=True, nullable=False)
    value: Any = Field(sa_column=Column(JSON, nullable=True))

    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_by_user_id: UUID | None = Field(default=None, nullable=True)

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubmissionFreezeRead(BaseModel):
    enabled: bool
    updated_at: datetime
    updated_by_user_id: UUID | None

    model_config = ConfigDict(from_attributes=True)


class SubmissionFreezeUpdate(BaseModel):
    enabled: bool


class PlatformSettingRead(BaseModel):
    name: str
    label: str | None
    group: str | None
    editable: bool
    secret: bool
    value: Any
    base_value: Any
    source: Literal["override", "environment", "default"]
    type: Literal["bool", "int", "float", "str", "choice"]
    options: list[str] | None
    option_labels: dict[str, str] | None
    minimum: float | None
    maximum: float | None
    description: str | None
    updated_at: datetime | None
    updated_by_user_id: UUID | None


class PlatformSettingsRead(BaseModel):
    settings: list[PlatformSettingRead]
    warnings: list[str]


class PlatformSettingsUpdate(BaseModel):
    # name -> new value; null resets the setting to its environment/default value.
    values: dict[str, Any]

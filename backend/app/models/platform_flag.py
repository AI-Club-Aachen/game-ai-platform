from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Field, SQLModel


# Known platform flag names.
SUBMISSION_FREEZE = "submission_freeze"


class PlatformFlag(SQLModel, table=True):
    """
    A named, admin-controlled platform-wide boolean toggle.

    Currently used for the submission freeze: while ``submission_freeze`` is
    enabled, non-admin users cannot create/delete submissions or agents, or
    change an agent's active submission — so entrants can't swap their code
    while a tournament runs.
    """

    __tablename__ = "platform_flags"

    name: str = Field(primary_key=True, nullable=False)
    enabled: bool = Field(default=False, nullable=False)

    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_by_user_id: UUID | None = Field(default=None, nullable=True)

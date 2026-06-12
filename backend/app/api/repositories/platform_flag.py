import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session

from app.models.platform_flag import PlatformFlag


logger = logging.getLogger(__name__)


class PlatformFlagRepositoryError(Exception):
    """Base exception for platform flag repository errors."""


class PlatformFlagRepository:
    """Repository for admin-controlled platform flags."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, name: str) -> PlatformFlag | None:
        return self._session.get(PlatformFlag, name)

    def is_enabled(self, name: str) -> bool:
        flag = self.get(name)
        return bool(flag and flag.enabled)

    def set_enabled(self, name: str, enabled: bool, updated_by_user_id: UUID | None = None) -> PlatformFlag:
        """Upsert a flag's value, handling commit/rollback."""
        flag = self.get(name) or PlatformFlag(name=name)
        flag.enabled = enabled
        flag.updated_at = datetime.now(UTC)
        flag.updated_by_user_id = updated_by_user_id
        try:
            self._session.add(flag)
            self._session.commit()
            self._session.refresh(flag)
        except Exception as e:
            self._session.rollback()
            logger.exception("Error setting platform flag %s", name)
            raise PlatformFlagRepositoryError("Failed to persist platform flag") from e
        else:
            return flag

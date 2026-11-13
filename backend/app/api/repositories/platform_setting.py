import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.models.platform_setting import PlatformSetting


logger = logging.getLogger(__name__)


class PlatformSettingRepositoryError(Exception):
    """Base exception for platform setting repository errors."""


class PlatformSettingRepository:
    """Repository for admin overrides of runtime-editable settings."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[PlatformSetting]:
        return list(self._session.exec(select(PlatformSetting)).all())

    def save(
        self,
        values: dict[str, Any],
        delete: Iterable[str] = (),
        updated_by_user_id: UUID | None = None,
    ) -> None:
        """Upsert ``values`` and delete the ``delete`` names in one transaction."""
        now = datetime.now(UTC)
        try:
            for name, value in values.items():
                row = self._session.get(PlatformSetting, name) or PlatformSetting(name=name)
                row.value = value
                row.updated_at = now
                row.updated_by_user_id = updated_by_user_id
                self._session.add(row)
            for name in delete:
                stale = self._session.get(PlatformSetting, name)
                if stale is not None:
                    self._session.delete(stale)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            logger.exception("Error saving platform settings")
            raise PlatformSettingRepositoryError("Failed to persist platform settings") from e

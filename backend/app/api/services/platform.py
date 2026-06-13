import logging
from uuid import UUID

from app.api.repositories.platform_flag import PlatformFlagRepository
from app.models.platform_flag import SUBMISSION_FREEZE, PlatformFlag


logger = logging.getLogger(__name__)


class PlatformService:
    """Service for admin-controlled platform-wide flags (e.g. the submission freeze)."""

    def __init__(self, flag_repository: PlatformFlagRepository) -> None:
        self._repository = flag_repository

    def get_submission_freeze(self) -> PlatformFlag:
        """Current submission-freeze flag, defaulting to a disabled (unsaved) flag."""
        return self._repository.get(SUBMISSION_FREEZE) or PlatformFlag(name=SUBMISSION_FREEZE, enabled=False)

    def is_submission_freeze_active(self) -> bool:
        return self._repository.is_enabled(SUBMISSION_FREEZE)

    def set_submission_freeze(self, enabled: bool, admin_user_id: UUID) -> PlatformFlag:
        logger.info("Submission freeze set to %s by admin %s", enabled, admin_user_id)
        return self._repository.set_enabled(SUBMISSION_FREEZE, enabled, updated_by_user_id=admin_user_id)

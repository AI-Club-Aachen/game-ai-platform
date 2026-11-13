import logging
from typing import Any
from uuid import UUID

from app.api.repositories.platform_setting import PlatformSettingRepository
from app.core import runtime_settings


logger = logging.getLogger(__name__)


class RuntimeSettingsService:
    """Reads and updates the admin overrides of runtime-editable settings."""

    def __init__(self, repository: PlatformSettingRepository) -> None:
        self._repository = repository

    def _stored(self) -> dict[str, Any]:
        return {row.name: row.value for row in self._repository.list_all()}

    def load(self) -> dict[str, Any]:
        """Apply the stored overrides onto ``settings`` (invalid ones are skipped)."""
        return runtime_settings.load_overrides(self._stored())

    def view(self) -> dict[str, Any]:
        overrides = runtime_settings.active_overrides()
        updated = {row.name: row for row in self._repository.list_all()}
        settings_list = runtime_settings.describe(overrides)
        for item in settings_list:
            row = updated.get(item["name"])
            item["updated_at"] = row.updated_at if row and item["source"] == "override" else None
            item["updated_by_user_id"] = row.updated_by_user_id if row and item["source"] == "override" else None
        return {"settings": settings_list, "warnings": runtime_settings.warnings()}

    def update(self, changes: dict[str, Any], admin_user_id: UUID | None) -> dict[str, Any]:
        """
        Apply ``changes`` (name -> value, or None to reset to the environment/default).

        All changes are validated together with the existing overrides before anything is
        saved, so an invalid value never reaches the database or the running settings.
        """
        stored = self._stored()
        current = runtime_settings.active_overrides()
        resets = {name for name, value in changes.items() if value is None}
        sets = {name: value for name, value in changes.items() if value is not None}
        merged = {name: value for name, value in {**current, **sets}.items() if name not in resets}
        unknown_resets = sorted(resets - runtime_settings.EDITABLE_SETTINGS.keys())
        if unknown_resets:
            raise runtime_settings.SettingsValidationError(
                dict.fromkeys(unknown_resets, "cannot be changed at runtime")
            )
        # Setting a value back to the environment/default value removes the override.
        validated = runtime_settings.drop_unchanged(runtime_settings.validate_overrides(merged))

        # Also drop stored rows that were skipped at startup (invalid or no longer editable).
        self._repository.save(
            {name: validated[name] for name in sets if name in validated},
            delete=stored.keys() - validated.keys(),
            updated_by_user_id=admin_user_id,
        )
        runtime_settings.apply_overrides(validated)
        logger.info("Settings changed by admin %s: %s", admin_user_id, changes)
        return self.view()

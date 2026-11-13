import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import CurrentAdmin, VerifiedGuestOrHigher, get_platform_service, get_runtime_settings_service
from app.api.services.platform import PlatformService
from app.api.services.runtime_settings import RuntimeSettingsService
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.runtime_settings import SettingsValidationError
from app.schemas.platform import (
    PlatformSettingsRead,
    PlatformSettingsUpdate,
    SubmissionFreezeRead,
    SubmissionFreezeUpdate,
)


logger = logging.getLogger(__name__)

router = APIRouter()


# GET /api/v1/platform/submission-freeze
@router.get("/submission-freeze", response_model=SubmissionFreezeRead)
def get_submission_freeze(
    _current_user: VerifiedGuestOrHigher,
    service: PlatformService = Depends(get_platform_service),
) -> SubmissionFreezeRead:
    """
    Current submission-freeze state. Readable by any verified user so the UI can
    show a banner and disable controls while a freeze is active.
    """
    return SubmissionFreezeRead.model_validate(service.get_submission_freeze())


# PUT /api/v1/platform/submission-freeze
@router.put("/submission-freeze", response_model=SubmissionFreezeRead)
@limiter.limit(lambda: settings.RATE_LIMIT_ADMIN)
def set_submission_freeze(
    request: Request,  # noqa: ARG001
    update: SubmissionFreezeUpdate,
    admin: CurrentAdmin,
    service: PlatformService = Depends(get_platform_service),
) -> SubmissionFreezeRead:
    """Enable or disable the platform-wide submission freeze. Admin only."""
    flag = service.set_submission_freeze(update.enabled, admin.id)
    return SubmissionFreezeRead.model_validate(flag)


def settings_validation_http_error(error: SettingsValidationError) -> HTTPException:
    """422 in FastAPI's validation-error shape, so the frontend shows every message."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=[
            {"loc": ["body", "values", name], "msg": f"{name}: {msg}", "type": "value_error"}
            for name, msg in error.errors.items()
        ],
    )


# GET /api/v1/platform/settings
@router.get("/settings", response_model=PlatformSettingsRead)
@limiter.limit(lambda: settings.RATE_LIMIT_ADMIN)
def get_platform_settings(
    request: Request,  # noqa: ARG001
    _admin: CurrentAdmin,
    service: RuntimeSettingsService = Depends(get_runtime_settings_service),
) -> PlatformSettingsRead:
    """Effective configuration with value sources; secrets are masked. Admin only."""
    return PlatformSettingsRead.model_validate(service.view())


# PUT /api/v1/platform/settings
@router.put("/settings", response_model=PlatformSettingsRead)
@limiter.limit(lambda: settings.RATE_LIMIT_ADMIN)
def update_platform_settings(
    request: Request,  # noqa: ARG001
    update: PlatformSettingsUpdate,
    admin: CurrentAdmin,
    service: RuntimeSettingsService = Depends(get_runtime_settings_service),
) -> PlatformSettingsRead:
    """Override runtime-editable settings (null resets one). Takes effect immediately. Admin only."""
    try:
        return PlatformSettingsRead.model_validate(service.update(update.values, admin.id))
    except SettingsValidationError as e:
        raise settings_validation_http_error(e) from e

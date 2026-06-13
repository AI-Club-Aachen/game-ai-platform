import logging

from fastapi import APIRouter, Depends, Request

from app.api.deps import CurrentAdmin, VerifiedGuestOrHigher, get_platform_service
from app.api.services.platform import PlatformService
from app.core.config import settings
from app.core.rate_limit import limiter
from app.schemas.platform import SubmissionFreezeRead, SubmissionFreezeUpdate


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

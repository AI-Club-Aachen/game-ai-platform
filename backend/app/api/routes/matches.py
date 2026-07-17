import asyncio
import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import (
    CurrentAdmin,
    VerifiedGuestOrHigher,
    VerifiedUserOrHigher,
    WorkerOrVerifiedUser,
    get_match_service,
    require_worker_api_key,
)
from app.api.services.match import (
    MatchPayloadTooLargeError,
    MatchPermissionError,
    MatchService,
    MatchServiceError,
)
from app.api.services.match_scheduler import (
    SCHEDULING_SERIAL,
    VALID_SCHEDULING_STRATEGIES,
)
from app.core.config import settings
from app.core.match_events import subscribe_match_events
from app.core.rate_limit import limiter
from app.models.game import GameType
from app.models.match import MatchStatus
from app.models.user import UserRole
from app.schemas.match import MatchCreate, MatchRead, MatchUpdate


logger = logging.getLogger(__name__)

router = APIRouter()


class MatchSchedulerConfig(BaseModel):
    enabled: bool
    interval_seconds: float
    strategy: str
    # "serial" (one at a time) or "concurrent" (fill up to MATCH_MAX_CONCURRENT_MATCHES)
    scheduling_strategy: str = SCHEDULING_SERIAL


@router.get("/scheduler/config", response_model=MatchSchedulerConfig)
@limiter.limit(lambda: settings.RATE_LIMIT_ADMIN)
def get_scheduler_config(
    request: Request,
    _admin: CurrentAdmin,
) -> MatchSchedulerConfig:
    """Get the current match scheduler configuration. Admin only."""
    task_runner = getattr(request.app.state, "task_runner", None)
    if not task_runner:
        raise HTTPException(status_code=500, detail="Task runner not found")

    for task in task_runner.tasks:
        if task.name == "match_scheduler":
            service = task.func.__self__ if hasattr(task.func, "__self__") else None
            strategy = getattr(service, "strategy", "random")
            scheduling_strategy = getattr(service, "scheduling_strategy", SCHEDULING_SERIAL)
            return MatchSchedulerConfig(
                enabled=task.is_enabled,
                interval_seconds=task.interval_seconds,
                strategy=strategy,
                scheduling_strategy=scheduling_strategy,
            )

    raise HTTPException(status_code=404, detail="Scheduler task not found")


@router.put("/scheduler/config", response_model=MatchSchedulerConfig)
@limiter.limit(lambda: settings.RATE_LIMIT_ADMIN)
def update_scheduler_config(
    config: MatchSchedulerConfig,
    request: Request,
    _admin: CurrentAdmin,
) -> MatchSchedulerConfig:
    """Update the match scheduler configuration. Admin only."""
    task_runner = getattr(request.app.state, "task_runner", None)
    if not task_runner:
        raise HTTPException(status_code=500, detail="Task runner not found")

    if config.scheduling_strategy not in VALID_SCHEDULING_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"scheduling_strategy must be one of {sorted(VALID_SCHEDULING_STRATEGIES)}",
        )

    for task in task_runner.tasks:
        if task.name == "match_scheduler":
            task.is_enabled = config.enabled
            task.interval_seconds = config.interval_seconds
            if hasattr(task.func, "__self__"):
                task.func.__self__.strategy = config.strategy
                task.func.__self__.scheduling_strategy = config.scheduling_strategy

            return MatchSchedulerConfig(
                enabled=task.is_enabled,
                interval_seconds=task.interval_seconds,
                strategy=config.strategy,
                scheduling_strategy=config.scheduling_strategy,
            )

    raise HTTPException(status_code=404, detail="Scheduler task not found")


# POST /api/v1/matches/
@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(lambda: settings.RATE_LIMIT_MATCH_CREATE)
async def create_match(
    request: Request,  # noqa: ARG001
    match_in: MatchCreate,
    current_user: VerifiedUserOrHigher,
    service: MatchService = Depends(get_match_service),
) -> MatchRead:
    """
    Create a new match request. Requires the USER role or higher; non-admin
    callers must own at least one of the participating agents.
    """
    try:
        return await service.create_match(
            arena_id=match_in.arena_id,
            config=match_in.config,
            agent_ids=match_in.agent_ids,
            owner_user_id=None if current_user.role == UserRole.ADMIN else current_user.id,
        )
    except MatchPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except MatchServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# GET /api/v1/matches/{match_id}
@router.get("/{match_id}", response_model=MatchRead)
def get_match(
    match_id: str,
    _actor: WorkerOrVerifiedUser,
    service: MatchService = Depends(get_match_service),
) -> MatchRead:
    """
    Get a match by ID. Requires a verified login (any role) or the worker API
    key (the match worker reads match data at run time).
    """
    match = service.get_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


# PATCH /api/v1/matches/{match_id}
@router.patch("/{match_id}", response_model=MatchRead, dependencies=[Depends(require_worker_api_key)])
async def update_match(
    match_id: str,
    update_data: MatchUpdate,
    service: MatchService = Depends(get_match_service),
) -> MatchRead:
    """
    Update a match. Worker API key required.
    """
    try:
        match = await service.update_match(
            match_id,
            status=update_data.status.value,
            logs=update_data.logs,
            result=update_data.result,
            game_state=update_data.game_state,
        )
    except MatchPayloadTooLargeError as e:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e)) from e
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


# GET /api/v1/matches/
@router.get("", response_model=list[MatchRead])
def list_matches(
    _current_user: VerifiedGuestOrHigher,
    service: MatchService = Depends(get_match_service),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    game_type: GameType | None = None,
    arena_id: UUID | None = None,
    status: Annotated[list[MatchStatus] | None, Query()] = None,
) -> list[MatchRead]:
    """
    List matches. Requires a verified login (any role).
    """
    return service.list_matches(skip, limit, game_type=game_type, arena_id=arena_id, status=status)


# GET /api/v1/matches/{match_id}/stream
@router.get("/{match_id}/stream")
@limiter.limit(lambda: settings.RATE_LIMIT_STREAM)
async def stream_match(
    request: Request,  # noqa: ARG001
    match_id: str,
    _current_user: VerifiedGuestOrHigher,
    service: MatchService = Depends(get_match_service),
) -> StreamingResponse:
    """
    Stream match game state updates via Server-Sent Events (SSE).

    - Sends the current game state immediately on connect.
    - For running matches, subscribes to Redis pub/sub and forwards
      real-time game state updates as SSE events.
    - Closes the stream when the match ends or the client disconnects.

    Requires a verified login (any role); spectating is not anonymous.
    """
    match = service.get_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    async def event_generator():  # noqa: ANN202
        # Send initial state immediately
        initial_event = {
            "game_state": match.game_state,
            "status": match.status.value,
            "game_type": match.game_type.value,
            "agent_ids": [str(aid) for aid in (match.agent_ids or [])],
            "logs": match.logs,
            "result": match.result,
        }
        yield f"data: {json.dumps(initial_event)}\n\n"

        # If match is already finished, close stream
        terminal_statuses = {MatchStatus.COMPLETED, MatchStatus.FAILED, MatchStatus.CLIENT_ERROR}
        if match.status in terminal_statuses:
            return

        # Subscribe to live updates via Redis pub/sub
        pubsub = await subscribe_match_events(match_id)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is not None and message["type"] == "message":
                    data = json.loads(message["data"])
                    event = {
                        "game_state": data.get("game_state"),
                        "status": data.get("status"),
                        "game_type": match.game_type.value,
                        "agent_ids": [str(aid) for aid in (match.agent_ids or [])],
                        "logs": data.get("logs"),
                        "result": data.get("result"),
                    }
                    yield f"data: {json.dumps(event)}\n\n"

                    # Close the stream if match entered a terminal state
                    if data.get("status") in {"completed", "failed", "client_error"}:
                        return
                else:
                    # Send a keep-alive comment every second to detect disconnects
                    yield ": keepalive\n\n"
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            logger.debug("SSE stream cancelled for match %s", match_id)
        finally:
            await pubsub.unsubscribe()
            await pubsub.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

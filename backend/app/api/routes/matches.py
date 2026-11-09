import asyncio
import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import (
    CurrentAdmin,
    VerifiedGuestOrHigher,
    VerifiedUserOrHigher,
    WorkerOrVerifiedUser,
    get_match_service,
    require_worker_api_key,
)
from app.api.services.match import (
    MatchConflictError,
    MatchNotFoundError,
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
from app.schemas.match import HumanMatchCreate, HumanMoveSubmit, MatchCreate, MatchRead, MatchUpdate


logger = logging.getLogger(__name__)

router = APIRouter()


class MatchSchedulerConfig(BaseModel):
    enabled: bool
    interval_seconds: float
    strategy: str
    # "serial" (one at a time) or "concurrent" (fill up to MATCH_MAX_CONCURRENT_MATCHES)
    scheduling_strategy: str = SCHEDULING_SERIAL
    # Human-vs-agent play: seconds per human move, and the cap for a whole game.
    human_move_time_limit: float = Field(default=settings.HUMAN_MOVE_TIME_LIMIT_SECONDS, ge=5.0, le=600.0)
    human_match_max_duration: float = Field(default=settings.HUMAN_MATCH_MAX_DURATION_SECONDS, ge=60.0, le=3600.0)


def _get_scheduler_service(request: Request) -> object | None:
    """The MatchSchedulerService instance registered on the app's task runner."""
    task_runner = getattr(request.app.state, "task_runner", None)
    if not task_runner:
        return None
    for task in task_runner.tasks:
        if task.name == "match_scheduler":
            return getattr(task.func, "__self__", None)
    return None


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
                human_move_time_limit=getattr(
                    service, "human_move_time_limit", settings.HUMAN_MOVE_TIME_LIMIT_SECONDS
                ),
                human_match_max_duration=getattr(
                    service, "human_match_max_duration", settings.HUMAN_MATCH_MAX_DURATION_SECONDS
                ),
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
                task.func.__self__.human_move_time_limit = config.human_move_time_limit
                task.func.__self__.human_match_max_duration = config.human_match_max_duration

            return MatchSchedulerConfig(
                enabled=task.is_enabled,
                interval_seconds=task.interval_seconds,
                strategy=config.strategy,
                scheduling_strategy=config.scheduling_strategy,
                human_move_time_limit=config.human_move_time_limit,
                human_match_max_duration=config.human_match_max_duration,
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


# POST /api/v1/matches/human
@router.post("/human", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(lambda: settings.RATE_LIMIT_MATCH_CREATE)
async def create_human_match(
    request: Request,
    match_in: HumanMatchCreate,
    current_user: VerifiedUserOrHigher,
    service: MatchService = Depends(get_match_service),
) -> MatchRead:
    """
    Start a game where the caller plays by hand against any agent of the arena.
    Requires the USER role or higher. One active human game per user; the
    result does not affect agent stats or ELO.
    """
    scheduler = _get_scheduler_service(request)
    move_limit = getattr(scheduler, "human_move_time_limit", settings.HUMAN_MOVE_TIME_LIMIT_SECONDS)
    max_duration = getattr(scheduler, "human_match_max_duration", settings.HUMAN_MATCH_MAX_DURATION_SECONDS)
    try:
        return await service.create_human_match(
            arena_id=match_in.arena_id,
            agent_id=match_in.agent_id,
            human_user_id=current_user.id,
            human_name=current_user.username,
            human_player_index=match_in.human_player_index,
            human_turn_time_limit=move_limit,
            max_duration_seconds=max_duration,
        )
    except MatchConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except MatchServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# GET /api/v1/matches/human/opponents?arena_id=...
@router.get("/human/opponents", response_model=list[dict])
def list_human_opponents(
    arena_id: UUID,
    current_user: VerifiedUserOrHigher,
    service: MatchService = Depends(get_match_service),
) -> list[dict]:
    """
    Agents of an arena you can play against by hand (any owner, working build).
    Requires the USER role or higher.
    """
    try:
        return service.list_human_opponents(arena_id, current_user.id)
    except MatchServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# POST /api/v1/matches/{match_id}/human-move
@router.post("/{match_id}/human-move", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(lambda: settings.RATE_LIMIT_MUTATIONS)
async def submit_human_move(
    request: Request,  # noqa: ARG001
    match_id: UUID,
    move_in: HumanMoveSubmit,
    current_user: VerifiedUserOrHigher,
    service: MatchService = Depends(get_match_service),
) -> dict[str, str]:
    """
    Submit a move as the human player. Accepted moves show up on the match's SSE
    stream; an illegal move is ignored by the runner (logged) and the turn stays yours.
    """
    try:
        await service.submit_human_move(str(match_id), current_user.id, move_in.move)
    except MatchNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except MatchPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except MatchConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except MatchPayloadTooLargeError as e:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e)) from e
    return {"status": "accepted"}


# POST /api/v1/matches/{match_id}/resign
@router.post("/{match_id}/resign", response_model=MatchRead)
@limiter.limit(lambda: settings.RATE_LIMIT_MUTATIONS)
async def resign_human_match(
    request: Request,  # noqa: ARG001
    match_id: UUID,
    current_user: VerifiedUserOrHigher,
    service: MatchService = Depends(get_match_service),
) -> MatchRead:
    """Resign (or cancel, if still queued) your human-vs-agent game."""
    try:
        return await service.resign_human_match(str(match_id), current_user.id)
    except MatchNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except MatchPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except MatchConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


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
            human_turn_seconds=update_data.human_turn_seconds,
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

    # Static for the match's lifetime: who sits where, and agent display names
    # (spectators can't list other users' agents, but names are public on leaderboards).
    static_fields = {
        "human_user_id": str(match.human_user_id) if match.human_user_id else None,
        "human_player_index": match.human_player_index,
        "human_name": match.human_name,
        "agent_names": service.get_agent_names(match.agent_ids or []),
    }

    async def event_generator():  # noqa: ANN202
        # Send initial state immediately
        initial_event = {
            "game_state": match.game_state,
            "status": match.status.value,
            "game_type": match.game_type.value,
            "agent_ids": [str(aid) for aid in (match.agent_ids or [])],
            "logs": match.logs,
            "result": match.result,
            "human_move_remaining": await service.get_human_move_remaining(match),
            **static_fields,
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
                        "human_move_remaining": data.get("human_move_remaining"),
                        **static_fields,
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

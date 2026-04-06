import asyncio
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_match_service, get_current_user
from app.api.services.match import MatchService, MatchServiceError
from app.core.match_events import subscribe_match_events
from app.models.game import GameType
from app.models.match import MatchStatus
from app.models.user import User
from app.schemas.match import MatchCreate, MatchRead, MatchUpdate


logger = logging.getLogger(__name__)

router = APIRouter()


# POST /api/v1/matches/
@router.post("", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
async def create_match(
    match_in: MatchCreate,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: MatchService = Depends(get_match_service),
) -> MatchRead:
    """
    Create a new match request.
    """
    try:
        return await service.create_match(match_in.game_type, match_in.config, match_in.agent_ids)
    except MatchServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# GET /api/v1/matches/{match_id}
@router.get("/{match_id}", response_model=MatchRead)
def get_match(
    match_id: str,
    service: MatchService = Depends(get_match_service),
) -> MatchRead:
    """
    Get a match by ID.
    """
    match = service.get_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


# PATCH /api/v1/matches/{match_id}
@router.patch("/{match_id}", response_model=MatchRead)
async def update_match(
    match_id: str,
    update_data: MatchUpdate,
    service: MatchService = Depends(get_match_service),
) -> MatchRead:
    """
    Update a match (used by workers).
    Note: This endpoint has no authentication for worker access.
    In production, consider adding API key authentication for workers.
    """
    match = await service.update_match(
        match_id,
        status=update_data.status.value,
        result=update_data.result,
        game_state=update_data.game_state,
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


# GET /api/v1/matches/
@router.get("", response_model=list[MatchRead])
def list_matches(
    service: MatchService = Depends(get_match_service),
    skip: int = 0,
    limit: int = 20,
    game_type: GameType | None = None,
    status: MatchStatus | None = None,
) -> list[MatchRead]:
    """
    List matches.
    """
    return service.list_matches(skip, limit, game_type=game_type, status=status)


# GET /api/v1/matches/{match_id}/stream
@router.get("/{match_id}/stream")
async def stream_match(
    match_id: str,
    service: MatchService = Depends(get_match_service),
) -> StreamingResponse:
    """
    Stream match game state updates via Server-Sent Events (SSE).

    - Sends the current game state immediately on connect.
    - For running matches, subscribes to Redis pub/sub and forwards
      real-time game state updates as SSE events.
    - Closes the stream when the match ends or the client disconnects.

    No authentication is required — spectating is public.
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
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message is not None and message["type"] == "message":
                    data = json.loads(message["data"])
                    event = {
                        "game_state": data.get("game_state"),
                        "status": data.get("status"),
                        "game_type": match.game_type.value,
                        "agent_ids": [str(aid) for aid in (match.agent_ids or [])],
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

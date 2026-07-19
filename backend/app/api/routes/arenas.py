from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import CurrentAdmin, VerifiedGuestOrHigher, WorkerOrVerifiedUser, get_arena_service
from app.api.services.arena import ArenaNotFoundError, ArenaService, ArenaValidationError
from app.core.config import settings
from app.core.rate_limit import limiter
from app.schemas.arena import ArenaCreate, ArenaRead, ArenaUpdate


router = APIRouter()


@router.post("", response_model=ArenaRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(lambda: settings.RATE_LIMIT_MUTATIONS)
def create_arena(
    request: Request,  # noqa: ARG001
    arena_create: ArenaCreate,
    _admin: CurrentAdmin,
    service: ArenaService = Depends(get_arena_service),
) -> ArenaRead:
    """
    Create a new arena. Admin only.
    """
    try:
        arena = service.create_arena(arena_create)
    except ArenaValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    else:
        # Convert password check to a boolean has_password
        read_obj = ArenaRead.model_validate(arena)
        read_obj.has_password = bool(arena.password)
        return read_obj


@router.get("", response_model=list[ArenaRead])
def list_arenas(
    _actor: WorkerOrVerifiedUser,
    service: ArenaService = Depends(get_arena_service),
) -> list[ArenaRead]:
    """
    List all active arenas.
    """
    arenas = service.list_active_arenas()
    result = []
    for arena in arenas:
        read_obj = ArenaRead.model_validate(arena)
        read_obj.has_password = bool(arena.password)
        result.append(read_obj)
    return result


@router.get("/all", response_model=list[ArenaRead])
def list_all_arenas(
    _admin: CurrentAdmin,
    service: ArenaService = Depends(get_arena_service),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ArenaRead]:
    """
    List all arenas (active and inactive). Admin only.
    """
    arenas, _ = service.list_all_arenas(skip=skip, limit=limit)
    result = []
    for arena in arenas:
        read_obj = ArenaRead.model_validate(arena)
        read_obj.has_password = bool(arena.password)
        result.append(read_obj)
    return result


@router.get("/{arena_id}", response_model=ArenaRead)
def get_arena(
    arena_id: UUID,
    _actor: WorkerOrVerifiedUser,
    service: ArenaService = Depends(get_arena_service),
) -> ArenaRead:
    """
    Get details of a specific arena.
    """
    try:
        arena = service.get_arena_by_id(arena_id)
    except ArenaNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    else:
        read_obj = ArenaRead.model_validate(arena)
        read_obj.has_password = bool(arena.password)
        return read_obj


@router.put("/{arena_id}", response_model=ArenaRead)
@limiter.limit(lambda: settings.RATE_LIMIT_MUTATIONS)
def update_arena(
    request: Request,  # noqa: ARG001
    arena_id: UUID,
    arena_update: ArenaUpdate,
    _admin: CurrentAdmin,
    service: ArenaService = Depends(get_arena_service),
) -> ArenaRead:
    """
    Update an arena. Admin only.
    """
    try:
        arena = service.update_arena(arena_id, arena_update)
    except ArenaNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ArenaValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    else:
        read_obj = ArenaRead.model_validate(arena)
        read_obj.has_password = bool(arena.password)
        return read_obj


@router.delete("/{arena_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(lambda: settings.RATE_LIMIT_MUTATIONS)
def delete_arena(
    request: Request,  # noqa: ARG001
    arena_id: UUID,
    _admin: CurrentAdmin,
    service: ArenaService = Depends(get_arena_service),
) -> None:
    """
    Soft-delete/deactivate an arena. Admin only.
    """
    try:
        service.delete_arena(arena_id)
    except ArenaNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

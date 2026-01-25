from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_match_service
from app.api.services.match import MatchService
from app.models.user import User
from app.schemas.match import MatchCreate, MatchRead, MatchUpdate


router = APIRouter()


# POST /api/v1/matches/
@router.post("/", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
async def create_match(
    match_in: MatchCreate,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: MatchService = Depends(get_match_service),
) -> MatchRead:
    """
    Create a new match request.
    """
    return await service.create_match(match_in.config)


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
def update_match(
    match_id: str,
    update_data: MatchUpdate,
    service: MatchService = Depends(get_match_service),
) -> MatchRead:
    """
    Update a match (used by workers).
    Note: This endpoint has no authentication for worker access.
    In production, consider adding API key authentication for workers.
    """
    match = service.update_match(
        match_id,
        status=update_data.status.value,
        logs=update_data.logs,
        result=update_data.result,
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


# GET /api/v1/matches/
@router.get("/", response_model=list[MatchRead])
def list_matches(
    service: MatchService = Depends(get_match_service),
    skip: int = 0,
    limit: int = 20,
) -> list[MatchRead]:
    """
    List matches.
    """
    return service.list_matches(skip, limit)

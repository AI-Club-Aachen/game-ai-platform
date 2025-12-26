from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_match_service
from app.api.services.match import MatchService
from app.models.user import User
from app.schemas.match import MatchCreate, MatchRead


router = APIRouter()


# POST /api/v1/matches/
@router.post("/", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
async def create_match(
    match_in: MatchCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: MatchService = Depends(get_match_service),
):
    """
    Create a new match request.
    """
    return await service.create_match(match_in.config)


# GET /api/v1/matches/{match_id}
@router.get("/{match_id}", response_model=MatchRead)
def get_match(
    match_id: str,
    service: MatchService = Depends(get_match_service),
):
    match = service.get_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


# GET /api/v1/matches/
@router.get("/", response_model=list[MatchRead])
def list_matches(
    service: MatchService = Depends(get_match_service),
    skip: int = 0,
    limit: int = 20,
):
    return service.list_matches(skip, limit)

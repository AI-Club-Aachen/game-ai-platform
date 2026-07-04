import logging
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import CurrentAdmin, VerifiedGuestOrHigher, get_tournament_service
from app.api.services.tournament import (
    TournamentNotFoundError,
    TournamentService,
    TournamentServiceError,
    TournamentStateError,
)
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.game import GameType
from app.models.tournament import TournamentStatus
from app.schemas.tournament import (
    MatchupResolveRequest,
    TournamentBracketRead,
    TournamentCreate,
    TournamentMatchupRead,
    TournamentRead,
)


logger = logging.getLogger(__name__)

router = APIRouter()


def _raise_for_service_error(e: TournamentServiceError) -> NoReturn:
    if isinstance(e, TournamentNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    if isinstance(e, TournamentStateError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# POST /api/v1/tournaments/
@router.post("", response_model=TournamentRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(lambda: settings.RATE_LIMIT_ADMIN)
def create_tournament(
    request: Request,  # noqa: ARG001
    tournament_in: TournamentCreate,
    _admin: CurrentAdmin,
    service: TournamentService = Depends(get_tournament_service),
) -> TournamentRead:
    """
    Create a tournament for one game type with an explicit set of entrant
    agents. Admin only.
    """
    try:
        return service.create_tournament(
            tournament_in.name,
            tournament_in.arena_id,
            tournament_in.agent_ids,
            tournament_in.config,
        )
    except TournamentServiceError as e:
        _raise_for_service_error(e)


# POST /api/v1/tournaments/{tournament_id}/start
@router.post("/{tournament_id}/start", response_model=TournamentRead)
@limiter.limit(lambda: settings.RATE_LIMIT_ADMIN)
async def start_tournament(
    request: Request,  # noqa: ARG001
    tournament_id: UUID,
    _admin: CurrentAdmin,
    service: TournamentService = Depends(get_tournament_service),
) -> TournamentRead:
    """
    Seed the bracket (random seeding and byes) and queue the first round.
    Admin only.
    """
    try:
        return await service.start_tournament(tournament_id)
    except TournamentServiceError as e:
        _raise_for_service_error(e)


# POST /api/v1/tournaments/{tournament_id}/cancel
@router.post("/{tournament_id}/cancel", response_model=TournamentRead)
@limiter.limit(lambda: settings.RATE_LIMIT_ADMIN)
def cancel_tournament(
    request: Request,  # noqa: ARG001
    tournament_id: UUID,
    _admin: CurrentAdmin,
    service: TournamentService = Depends(get_tournament_service),
) -> TournamentRead:
    """Cancel a tournament. Admin only."""
    try:
        return service.cancel_tournament(tournament_id)
    except TournamentServiceError as e:
        _raise_for_service_error(e)


# POST /api/v1/tournaments/{tournament_id}/matchups/{matchup_id}/resolve
@router.post("/{tournament_id}/matchups/{matchup_id}/resolve", response_model=TournamentMatchupRead)
@limiter.limit(lambda: settings.RATE_LIMIT_ADMIN)
def resolve_matchup(
    request: Request,  # noqa: ARG001
    tournament_id: UUID,
    matchup_id: UUID,
    resolve_in: MatchupResolveRequest,
    _admin: CurrentAdmin,
    service: TournamentService = Depends(get_tournament_service),
) -> TournamentMatchupRead:
    """
    Resolve a matchup stuck in NEEDS_ATTENTION (e.g. repeated infrastructure
    failures) by declaring its winner. Admin only.
    """
    try:
        return service.resolve_matchup(tournament_id, matchup_id, resolve_in.winner_agent_id)
    except TournamentServiceError as e:
        _raise_for_service_error(e)


# GET /api/v1/tournaments/
@router.get("", response_model=list[TournamentRead])
def list_tournaments(
    _current_user: VerifiedGuestOrHigher,
    service: TournamentService = Depends(get_tournament_service),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    game_type: GameType | None = None,
    arena_id: UUID | None = None,
    status: TournamentStatus | None = None,
) -> list[TournamentRead]:
    """
    List tournaments. Requires a verified login (any role).
    """
    return service.list_tournaments(skip, limit, game_type=game_type, arena_id=arena_id, status=status)


# GET /api/v1/tournaments/{tournament_id}
@router.get("/{tournament_id}", response_model=TournamentRead)
def get_tournament(
    tournament_id: UUID,
    _current_user: VerifiedGuestOrHigher,
    service: TournamentService = Depends(get_tournament_service),
) -> TournamentRead:
    """
    Get a tournament by ID. Requires a verified login (any role).
    """
    tournament = service.get_tournament(tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament


# GET /api/v1/tournaments/{tournament_id}/bracket
@router.get("/{tournament_id}/bracket", response_model=TournamentBracketRead)
def get_tournament_bracket(
    tournament_id: UUID,
    _current_user: VerifiedGuestOrHigher,
    service: TournamentService = Depends(get_tournament_service),
) -> TournamentBracketRead:
    """
    Full bracket and standings for a tournament. Requires a verified login
    (any role).
    """
    try:
        bracket = service.get_bracket(tournament_id)
    except TournamentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return TournamentBracketRead(
        tournament=bracket["tournament"],
        entrants=bracket["entrants"],
        matchups=[
            TournamentMatchupRead.model_validate({**item["matchup"].model_dump(), "games": item["games"]})
            for item in bracket["matchups"]
        ],
        standings=bracket["standings"],
    )

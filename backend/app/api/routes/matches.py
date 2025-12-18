from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.session import get_session
from app.api.deps import get_current_user
from app.core.queue import job_queue
from app.models.match import Match, MatchStatus
from app.models.user import User
from app.schemas.match import MatchCreate, MatchRead

router = APIRouter()


@router.post("/", response_model=MatchRead, status_code=status.HTTP_201_CREATED)
async def create_match(
    match_in: MatchCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_session),
):
    """
    Create a new match request.
    """
    match = Match(
        status=MatchStatus.QUEUED,
        config=match_in.config
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    # Enqueue job
    await job_queue.enqueue_match(match.id, match.config)

    return match


@router.get("/{match_id}", response_model=MatchRead)
def get_match(
    match_id: str,
    db: Session = Depends(get_session),
):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.get("/", response_model=list[MatchRead])
def list_matches(
    db: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 20,
):
    query = select(Match).offset(skip).limit(limit)
    return db.exec(query).all()

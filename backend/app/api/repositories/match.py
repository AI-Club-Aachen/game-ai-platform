import logging
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlmodel import Session, func, select

from app.models.match import Match, MatchStatus


logger = logging.getLogger(__name__)


class MatchRepositoryError(Exception):
    """Base exception for match repository errors."""


class MatchRepository:
    """Repository for Match aggregate."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Queries ---

    def get_by_id(self, match_id: str) -> Match | None:
        return self._session.get(Match, match_id)

    def list_by_ids(self, match_ids: list[UUID]) -> Sequence[Match]:
        if not match_ids:
            return []
        statement = select(Match).where(Match.id.in_(match_ids))
        return self._session.exec(statement).all()

    def list_matches(
        self,
        skip: int,
        limit: int,
        game_type: str | None = None,
        arena_id: UUID | None = None,
        status: list[str] | str | None = None,
        with_tournament: bool | None = None,
    ) -> Sequence[Match]:
        """List matches with pagination.

        ``with_tournament`` filters by tournament membership: True keeps only
        tournament matches, False only normal matches, None keeps all.
        """
        statement = select(Match)
        if game_type is not None:
            statement = statement.where(Match.game_type == game_type)
        if arena_id is not None:
            statement = statement.where(Match.arena_id == arena_id)
        if status is not None:
            if isinstance(status, (list, tuple, set)):
                if len(status) > 0:
                    statement = statement.where(Match.status.in_(status))
            else:
                statement = statement.where(Match.status == status)
        if with_tournament is True:
            statement = statement.where(Match.tournament_id.is_not(None))
        elif with_tournament is False:
            statement = statement.where(Match.tournament_id.is_(None))

        statement = statement.offset(skip).limit(limit).order_by(Match.created_at.desc())
        return self._session.exec(statement).all()

    def list_stale_running_matches(
        self,
        cutoff: datetime,
        limit: int = 100,
        with_tournament: bool | None = None,
    ) -> Sequence[Match]:
        """List running matches that have not been updated since ``cutoff``."""
        statement = (
            select(Match)
            .where(Match.status == MatchStatus.RUNNING)
            .where(Match.updated_at < cutoff)
            .order_by(Match.updated_at.asc())
            .limit(limit)
        )
        if with_tournament is True:
            statement = statement.where(Match.tournament_id.is_not(None))
        elif with_tournament is False:
            statement = statement.where(Match.tournament_id.is_(None))
        return self._session.exec(statement).all()

    def count_active_by_tournament(self, tournament_id: UUID) -> int:
        """Number of queued/running matches belonging to a tournament (concurrency cap)."""
        statement = (
            select(func.count())
            .select_from(Match)
            .where(Match.tournament_id == tournament_id)
            .where(Match.status.in_([MatchStatus.QUEUED, MatchStatus.RUNNING]))
        )
        return self._session.exec(statement).one()

    def count_active_non_tournament(self) -> int:
        """Number of queued/running non-tournament matches (auto-scheduler concurrency cap)."""
        statement = (
            select(func.count())
            .select_from(Match)
            .where(Match.tournament_id.is_(None))
            .where(Match.status.in_([MatchStatus.QUEUED, MatchStatus.RUNNING]))
        )
        return self._session.exec(statement).one()

    # --- Commands ---

    def save(self, match: Match) -> Match:
        """Persist match, handling commit/rollback."""
        try:
            self._session.add(match)
            self._session.commit()
            self._session.refresh(match)
        except Exception as e:
            self._session.rollback()
            logger.exception("Error saving match %s", getattr(match, "id", None))
            raise MatchRepositoryError("Failed to persist match") from e
        else:
            return match

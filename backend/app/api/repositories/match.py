import logging
from collections.abc import Sequence

from sqlmodel import Session, select

from app.models.match import Match


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

    def list_matches(
        self,
        skip: int,
        limit: int,
    ) -> Sequence[Match]:
        """List matches with pagination."""
        statement = select(Match).offset(skip).limit(limit).order_by(Match.created_at.desc())
        return self._session.exec(statement).all()

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

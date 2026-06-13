import logging
from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, select

from app.models.tournament import (
    Tournament,
    TournamentEntrant,
    TournamentGame,
    TournamentMatchup,
    TournamentStatus,
)


logger = logging.getLogger(__name__)


class TournamentRepositoryError(Exception):
    """Base exception for tournament repository errors."""


class TournamentRepository:
    """Repository for the Tournament aggregate (tournament, entrants, matchups, games)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Queries ---

    def get_by_id(self, tournament_id: UUID) -> Tournament | None:
        return self._session.get(Tournament, tournament_id)

    def list_tournaments(
        self,
        skip: int,
        limit: int,
        game_type: str | None = None,
        status: str | None = None,
    ) -> Sequence[Tournament]:
        """List tournaments with pagination."""
        statement = select(Tournament)
        if game_type is not None:
            statement = statement.where(Tournament.game_type == game_type)
        if status is not None:
            statement = statement.where(Tournament.status == status)

        statement = statement.offset(skip).limit(limit).order_by(Tournament.created_at.desc())
        return self._session.exec(statement).all()

    def list_active(self) -> Sequence[Tournament]:
        """Tournaments the scheduler must advance (running or flagged for attention)."""
        statement = select(Tournament).where(
            Tournament.status.in_([TournamentStatus.RUNNING, TournamentStatus.NEEDS_ATTENTION])
        )
        return self._session.exec(statement).all()

    def list_entrants(self, tournament_id: UUID) -> Sequence[TournamentEntrant]:
        statement = (
            select(TournamentEntrant)
            .where(TournamentEntrant.tournament_id == tournament_id)
            .order_by(TournamentEntrant.created_at.asc())
        )
        return self._session.exec(statement).all()

    def list_matchups(self, tournament_id: UUID) -> Sequence[TournamentMatchup]:
        statement = (
            select(TournamentMatchup)
            .where(TournamentMatchup.tournament_id == tournament_id)
            .order_by(TournamentMatchup.stage.asc(), TournamentMatchup.position.asc())
        )
        return self._session.exec(statement).all()

    def get_matchup(self, matchup_id: UUID) -> TournamentMatchup | None:
        return self._session.get(TournamentMatchup, matchup_id)

    def list_games(self, tournament_id: UUID) -> Sequence[TournamentGame]:
        statement = (
            select(TournamentGame)
            .where(TournamentGame.tournament_id == tournament_id)
            .order_by(TournamentGame.game_index.asc())
        )
        return self._session.exec(statement).all()

    # --- Commands ---

    def save(self, tournament: Tournament) -> Tournament:
        """Persist tournament, handling commit/rollback."""
        try:
            self._session.add(tournament)
            self._session.commit()
            self._session.refresh(tournament)
        except Exception as e:
            self._session.rollback()
            logger.exception("Error saving tournament %s", getattr(tournament, "id", None))
            raise TournamentRepositoryError("Failed to persist tournament") from e
        else:
            return tournament

    def save_entrant(self, entrant: TournamentEntrant) -> TournamentEntrant:
        try:
            self._session.add(entrant)
            self._session.commit()
            self._session.refresh(entrant)
        except Exception as e:
            self._session.rollback()
            logger.exception("Error saving tournament entrant %s", getattr(entrant, "id", None))
            raise TournamentRepositoryError("Failed to persist tournament entrant") from e
        else:
            return entrant

    def save_matchup(self, matchup: TournamentMatchup) -> TournamentMatchup:
        try:
            self._session.add(matchup)
            self._session.commit()
            self._session.refresh(matchup)
        except Exception as e:
            self._session.rollback()
            logger.exception("Error saving tournament matchup %s", getattr(matchup, "id", None))
            raise TournamentRepositoryError("Failed to persist tournament matchup") from e
        else:
            return matchup

    def save_game(self, game: TournamentGame) -> TournamentGame:
        try:
            self._session.add(game)
            self._session.commit()
            self._session.refresh(game)
        except Exception as e:
            self._session.rollback()
            logger.exception("Error saving tournament game %s", getattr(game, "id", None))
            raise TournamentRepositoryError("Failed to persist tournament game") from e
        else:
            return game

    def save_all(
        self,
        objects: Sequence[Tournament | TournamentEntrant | TournamentMatchup | TournamentGame],
    ) -> None:
        """Persist several tournament objects in a single commit (e.g. bracket seeding)."""
        try:
            for obj in objects:
                self._session.add(obj)
            self._session.commit()
            for obj in objects:
                self._session.refresh(obj)
        except Exception as e:
            self._session.rollback()
            logger.exception("Error saving %d tournament objects", len(objects))
            raise TournamentRepositoryError("Failed to persist tournament objects") from e

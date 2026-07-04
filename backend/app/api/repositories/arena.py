import logging
from uuid import UUID

from sqlmodel import Session, select

from app.models.arena import Arena


logger = logging.getLogger(__name__)


class ArenaRepositoryError(Exception):
    """Base exception for arena repository errors."""


class ArenaRepository:
    """Repository for Arena aggregate."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Queries ---

    def get_by_id(self, arena_id: str | UUID) -> Arena | None:
        if isinstance(arena_id, str):
            try:
                arena_id = UUID(arena_id)
            except ValueError:
                return None
        return self._session.get(Arena, arena_id)

    def list_active(self) -> list[Arena]:
        """List active arenas."""
        statement = select(Arena).where(Arena.is_active == True).order_by(Arena.name.asc())
        return list(self._session.exec(statement).all())

    def list_all(self, skip: int = 0, limit: int = 100) -> tuple[list[Arena], int]:
        """List all arenas (active and inactive) for admin management."""
        statement = select(Arena).offset(skip).limit(limit).order_by(Arena.name.asc())
        count_statement = select(Arena)
        # Note: we can count all using len of execution or select count
        total = len(self._session.exec(count_statement).all())
        return list(self._session.exec(statement).all()), total

    # --- Commands ---

    def save(self, arena: Arena) -> Arena:
        """Persist arena, handling commit/rollback."""
        try:
            self._session.add(arena)
            self._session.commit()
            self._session.refresh(arena)
        except Exception as e:
            self._session.rollback()
            logger.exception("Error saving arena %s", getattr(arena, "id", None))
            raise ArenaRepositoryError("Failed to persist arena") from e
        else:
            return arena

    def delete(self, arena: Arena) -> None:
        """Delete arena, handling commit/rollback."""
        try:
            self._session.delete(arena)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            logger.exception("Error deleting arena %s", arena.id)
            raise ArenaRepositoryError("Failed to delete arena") from e

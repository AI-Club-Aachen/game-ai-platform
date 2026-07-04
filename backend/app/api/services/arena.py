import logging
from datetime import UTC, datetime
from uuid import UUID

from app.api.repositories.arena import ArenaRepository, ArenaRepositoryError
from app.models.arena import Arena
from app.schemas.arena import ArenaCreate, ArenaUpdate

logger = logging.getLogger(__name__)


class ArenaServiceError(Exception):
    """Base exception for arena service errors."""


class ArenaNotFoundError(ArenaServiceError):
    """Raised when an arena cannot be found."""


class ArenaValidationError(ArenaServiceError):
    """Raised when validation fails."""


class ArenaService:
    """Service for managing arenas."""

    def __init__(self, repository: ArenaRepository) -> None:
        self._repository = repository

    def get_arena_by_id(self, arena_id: UUID | str) -> Arena:
        """Get an arena by ID or raise ArenaNotFoundError."""
        arena = self._repository.get_by_id(arena_id)
        if not arena:
            raise ArenaNotFoundError("Arena not found")
        return arena

    def list_active_arenas(self) -> list[Arena]:
        """List all active arenas."""
        try:
            return self._repository.list_active()
        except ArenaRepositoryError as e:
            logger.exception("Error listing active arenas")
            raise ArenaServiceError("Failed to list active arenas") from e

    def list_all_arenas(self, skip: int = 0, limit: int = 100) -> tuple[list[Arena], int]:
        """List all arenas (for admin)."""
        try:
            return self._repository.list_all(skip=skip, limit=limit)
        except ArenaRepositoryError as e:
            logger.exception("Error listing all arenas")
            raise ArenaServiceError("Failed to list all arenas") from e

    def create_arena(self, arena_create: ArenaCreate) -> Arena:
        """Create a new arena."""
        # Simple configuration validation: ensure turn_time_limit exists or other fields are valid
        if "turn_time_limit" in arena_create.config:
            limit = arena_create.config["turn_time_limit"]
            if not isinstance(limit, (int, float)) or limit <= 0:
                raise ArenaValidationError("turn_time_limit must be a positive number")

        # Create model instance
        arena = Arena(
            name=arena_create.name,
            game_type=arena_create.game_type,
            description=arena_create.description,
            config=arena_create.config,
            password=arena_create.password if arena_create.password else None,
            is_active=arena_create.is_active,
        )
        try:
            return self._repository.save(arena)
        except ArenaRepositoryError as e:
            logger.exception("Error creating arena")
            raise ArenaServiceError("Failed to create arena") from e

    def update_arena(self, arena_id: UUID, arena_update: ArenaUpdate) -> Arena:
        """Update an existing arena."""
        arena = self.get_arena_by_id(arena_id)

        update_dict = arena_update.model_dump(exclude_unset=True)

        if "config" in update_dict and update_dict["config"] is not None:
            config = update_dict["config"]
            if "turn_time_limit" in config:
                limit = config["turn_time_limit"]
                if not isinstance(limit, (int, float)) or limit <= 0:
                    raise ArenaValidationError("turn_time_limit must be a positive number")

        for key, value in update_dict.items():
            if key == "password" and value == "":
                arena.password = None
            else:
                setattr(arena, key, value)

        arena.updated_at = datetime.now(UTC)

        try:
            return self._repository.save(arena)
        except ArenaRepositoryError as e:
            logger.exception("Error updating arena %s", arena_id)
            raise ArenaServiceError("Failed to update arena") from e

    def delete_arena(self, arena_id: UUID) -> None:
        """Deactivate/delete an arena."""
        # For safety and data integrity, we perform a soft-delete (setting is_active=False)
        arena = self.get_arena_by_id(arena_id)
        arena.is_active = False
        arena.updated_at = datetime.now(UTC)
        try:
            self._repository.save(arena)
        except ArenaRepositoryError as e:
            logger.exception("Error deactivating arena %s", arena_id)
            raise ArenaServiceError("Failed to deactivate arena") from e

    def verify_arena_password(self, arena_id: UUID, password: str | None) -> bool:
        """Verify the password for an arena. Returns True if password matches or not required."""
        arena = self.get_arena_by_id(arena_id)
        if not arena.password:
            return True
        return arena.password == password

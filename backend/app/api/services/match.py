from collections.abc import Sequence
from typing import Any

from app.api.repositories.match import MatchRepository
from app.core.queue import job_queue
from app.models.match import Match, MatchStatus


class MatchServiceError(Exception):
    """Base exception for match service errors."""


class MatchService:
    """Service for managing matches."""

    def __init__(self, match_repository: MatchRepository) -> None:
        self._repository = match_repository

    async def create_match(
        self,
        config: dict[str, Any],
    ) -> Match:
        """
        Create a match and queue it for execution.
        """
        match = Match(status=MatchStatus.QUEUED, config=config)
        match = self._repository.save(match)

        # Enqueue job
        await job_queue.enqueue_match(match.id, match.config)

        return match

    def get_match(self, match_id: str) -> Match | None:
        return self._repository.get_by_id(match_id)

    def list_matches(
        self,
        skip: int,
        limit: int,
    ) -> Sequence[Match]:
        return self._repository.list_matches(skip, limit)

import logging
from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.api.repositories.agent import AgentRepository
from app.api.repositories.arena import ArenaRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.match import MatchRepository
from app.api.repositories.tournament import TournamentRepository
from app.api.services.match import MatchService
from app.api.services.tournament import TournamentService
from app.core.config import settings
from app.db.connection import engine
from app.models.match import MatchStatus


logger = logging.getLogger(__name__)


class TournamentSchedulerService:
    """
    Advances running tournaments in the background.

    Each tick re-derives all tournament state from the database (no in-memory
    state), so it is idempotent and safe across backend restarts: completed
    games are recorded, brackets advance round by round, and new matches are
    queued up to each tournament's concurrency cap.
    """

    async def check_and_advance_tournaments(self) -> None:
        with Session(engine) as session:
            tournament_repository = TournamentRepository(session)
            match_repository = MatchRepository(session)
            agent_repository = AgentRepository(session)
            job_repository = JobRepository(session)
            arena_repository = ArenaRepository(session)
            match_service = MatchService(match_repository, job_repository, agent_repository, arena_repository)
            tournament_service = TournamentService(
                tournament_repository, match_repository, agent_repository, match_service, arena_repository
            )

            await self._fail_stale_tournament_matches(match_repository, match_service)

            for tournament in tournament_repository.list_active():
                try:
                    await tournament_service.advance_tournament(tournament)
                except Exception:
                    logger.exception("Error advancing tournament %s", tournament.id)

    async def _fail_stale_tournament_matches(
        self,
        match_repository: MatchRepository,
        match_service: MatchService,
    ) -> None:
        """
        Recover tournament matches abandoned by a killed/restarted worker, mirroring
        the match scheduler's stale handling (which skips tournament matches). The
        resulting FAILED status flows into the normal retry/needs-attention path.
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.MATCH_STALE_TIMEOUT_SECONDS)
        stale_matches = match_repository.list_stale_running_matches(cutoff=cutoff, with_tournament=True)
        for match in stale_matches:
            logger.warning(
                "Marking stale running tournament match %s as failed; last update at %s exceeded %ss timeout",
                match.id,
                match.updated_at,
                settings.MATCH_STALE_TIMEOUT_SECONDS,
            )
            await match_service.update_match(
                str(match.id),
                status=MatchStatus.FAILED.value,
                result={
                    "status": "error",
                    "reason": "Match runner lost or timed out",
                    "details": (
                        "Match remained in running state without worker updates beyond "
                        f"{settings.MATCH_STALE_TIMEOUT_SECONDS} seconds."
                    ),
                },
            )

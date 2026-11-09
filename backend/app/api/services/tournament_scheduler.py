import logging

from sqlmodel import Session

from app.api.repositories.agent import AgentRepository
from app.api.repositories.arena import ArenaRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.match import MatchRepository
from app.api.repositories.tournament import TournamentRepository
from app.api.services.match import MatchService
from app.api.services.tournament import TournamentService
from app.db.connection import engine


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

            # FAILED then flows into the normal retry/needs-attention path.
            await match_service.fail_stale_running_matches(with_tournament=True)

            for tournament in tournament_repository.list_active():
                try:
                    await tournament_service.advance_tournament(tournament)
                except Exception:
                    logger.exception("Error advancing tournament %s", tournament.id)

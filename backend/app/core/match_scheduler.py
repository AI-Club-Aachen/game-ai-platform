import logging
import random
from collections import defaultdict

from app.api.repositories.agent import AgentRepository
from app.api.repositories.match import MatchRepository
from app.api.services.match import MatchService
from app.api.services.submission_builds import submission_has_successful_build
from app.models.game import GameType
from app.models.match import MatchConfig, MatchStatus

logger = logging.getLogger(__name__)


class MatchScheduler:
    """
    Manages the scheduling of matches based on certain criteria.
    """

    def __init__(
        self,
        match_repository: MatchRepository,
        agent_repository: AgentRepository,
        match_service: MatchService,
    ):
        self._match_repository = match_repository
        self._agent_repository = agent_repository
        self._match_service = match_service

    async def check_and_queue_matches(self):
        """
        Check if new matches need to be queued and enqueue them if necessary.
        This method can be called periodically by a background task.
        """
        logger.info("Checking if new matches need to be queued...")

        # Check the current match queue and determine if new matches should be added
        if not self.check_match_queue():
            logger.info("No new matches need to be queued at this time.")
            return

        # Get available agents that can be scheduled for matches
        available_agents = self.get_available_agents()

        # remove game types with less than 2 available agents
        available_agents = {game_type: agents for game_type, agents in available_agents.items() if len(agents) >= 2}
        if not available_agents:
            logger.info("No game types have enough available agents to schedule matches.")
            return

        # randomly choose a game type and agents for the match
        game_type_str = random.choice(list(available_agents.keys()))
        agents_for_match = self.choose_agents_for_match(available_agents[game_type_str])

        # Create and enqueue a new match with the selected agents
        try:
            game_type = GameType(game_type_str)
            config = MatchConfig()
            match = await self._match_service.create_match(
                game_type=game_type,
                config=config,
                agent_ids=agents_for_match,
            )
            logger.info(f"Queued a new match for game type '{game_type_str}' with agents: {agents_for_match}, match_id: {match.id}")
        except Exception as e:
            logger.exception(f"Error creating match for game type '{game_type_str}' with agents {agents_for_match}")

    def check_match_queue(self) -> bool:
        """
        Check the current match queue and determine if new matches should be added.
        Matches are added as long as no match is in queue or running for any game type.
        """
        # Check if any matches are currently queued
        queued_matches = self._match_repository.list_matches(
            skip=0, limit=1, status=MatchStatus.QUEUED.value
        )
        if queued_matches:
            return False

        # Check if any matches are currently running
        running_matches = self._match_repository.list_matches(
            skip=0, limit=1, status=MatchStatus.RUNNING.value
        )
        if running_matches:
            return False

        # No matches are queued or running, so new matches can be queued
        return True

    def get_available_agents(self) -> dict:
        """
        Get a list of available agents that can be scheduled for matches.
        Returns a dictionary of game type to agent ids.
        """
        # Get all agents, fetching in batches
        available_by_game_type = defaultdict(list)

        skip = 0
        limit = 100

        while True:
            agents, total = self._agent_repository.list_agents(skip=skip, limit=limit)
            if not agents:
                break

            # Filter agents that have active submissions with successful builds
            for agent in agents:
                if agent.active_submission and submission_has_successful_build(agent.active_submission):
                    available_by_game_type[agent.game_type].append(agent.id)

            skip += limit
            if skip >= total:
                break

        return dict(available_by_game_type)   

    def choose_agents_for_match(self, available_agents) -> list:
        """
        Choose a set of agents to participate in a new match based on your scheduling criteria.
        This is a placeholder method and should be implemented with your specific logic.
        """
        # Implement logic to select agents for a match based on criteria (e.g., skill level, recent activity)
        return available_agents[:2]  # Example: just take the first 2 available agents

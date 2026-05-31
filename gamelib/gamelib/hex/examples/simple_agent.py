"""
A simple agent that plays a random valid move in Hex.
"""

import os
import random
from typing import override

from gamelib.hex.agent import Agent
from gamelib.hex.dev_runner import DevRunner
from gamelib.hex.gamestate import GameState as State
from gamelib.hex.move import Move


class HexAgent(Agent):
    """
    A simple Hex agent that picks a random available cell.
    """

    @override
    def initialize(self, init_data: dict) -> None:
        """Initialize the agent."""
        self.player_id = init_data["player_id"]

    @override
    def get_move(self, state: State) -> Move:
        """Find a random empty cell and return as move."""
        empty_cells = [(r, c) for r in range(state.board_size) for c in range(state.board_size) if state.board[r][c] == -1]
        if not empty_cells:
            raise ValueError("No valid moves available.")

        position = random.choice(empty_cells)
        return Move(player=self.player_id, position=list(position))


if __name__ == "__main__":
    # Check if running in online mode or local development mode
    # No need to set any environment variable for local testing
    ONLINE = os.getenv("AGENT_ONLINE", "0") == "1"
    if ONLINE:
        # Online submission runner
        agent = HexAgent()
        agent.start()
    else:
        # Local development runner
        runner = DevRunner()
        agent1 = HexAgent()
        agent2 = HexAgent()
        runner.add_agent(agent1)
        runner.add_agent(agent2)
        runner.start()


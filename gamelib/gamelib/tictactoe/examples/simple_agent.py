"""
Sample Tic-Tac-Toe Agent Implementation.
"""

import os
from typing import override

from gamelib.tictactoe import Agent, DevRunner, Move
from gamelib.tictactoe import GameState as State


class TicTacToeAgent(Agent):
    """
    A simple Tic-Tac-Toe agent that selects the first available cell.
    """

    @override
    def initialize(self, agent_init_data: dict) -> None:
        """
        Initialize the Tic-Tac-Toe agent before the game starts.
        This is used instead of __init__.
        The ini data was read in the base class in "_read_init" and passed here.
        Args:
            agent_init_data (dict): Initialization data for the agent.
        """
        self.player_id = agent_init_data["player_id"]

    @override
    def get_move(self, game_state: State) -> Move:
        """
        Decide on a move based on the given Tic-Tac-Toe game state.
        This simple agent selects the first available cell.
        Args:
            game_state (State): The current game state.
        Returns:
            Move: The selected move.
        """
        for position in range(9):
            if game_state.board[position] == -1:  # Check for empty cell
                return Move(player=self.player_id, position=position)
        raise ValueError("No valid moves available.")


if __name__ == "__main__":
    # Check if running in online mode or local development mode
    # No need to set any environment variable for local testing
    ONLINE = os.getenv("AGENT_ONLINE", "0") == "1"
    if ONLINE:
        # Online submission runner
        agent = TicTacToeAgent()
        agent.start()
    else:
        # Local development runner
        runner = DevRunner()
        agent1 = TicTacToeAgent()
        agent2 = TicTacToeAgent()
        runner.add_agent(agent1)
        runner.add_agent(agent2)
        runner.start()

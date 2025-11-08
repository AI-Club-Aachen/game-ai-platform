"""
Sample Tic-Tac-Toe Agent Implementation.
"""

from gamelib.tictactoe.gamestate import State
from gamelib.tictactoe.agent import Agent
from gamelib.tictactoe.move import Move


class TicTacToeAgent(Agent):
    """
    A simple Tic-Tac-Toe agent that selects the first available cell.
    """

    def initialize(self, init_data: dict):
        """
        Initialize the Tic-Tac-Toe agent before the game starts.
        This is used instead of __init__.
        """
        self.player_id = init_data["player_id"]

    def get_move(self, state: State) -> Move:
        """
        Decide on a move based on the current Tic-Tac-Toe game state.
        This simple agent selects the first available cell.
        """
        for position in range(9):
            if state.board[position] == -1:  # Check for empty cell
                return Move(player=self.player_id, position=position)
        raise Exception("No valid moves available.")

"""
Sample Tic-Tac-Toe Agent Implementation.
"""

from typing import override

from gamelib.tictactoe.gamestate import GameState as State
from gamelib.tictactoe.agent import Agent
from gamelib.tictactoe.move import Move


class TicTacToeAgent(Agent):
    """
    A simple Tic-Tac-Toe agent that selects the first available cell.
    """

    @override
    def initialize(self, init_data: dict):
        """
        Initialize the Tic-Tac-Toe agent before the game starts.
        This is used instead of __init__.
        """
        self.player_id = init_data["player_id"]

    @override
    def get_move(self, game_state: State) -> Move:
        """
        Decide on a move based on the given Tic-Tac-Toe game state.
        This simple agent selects the first available cell.
        """
        for position in range(9):
            if game_state.board[position] == -1:  # Check for empty cell
                return Move(player=self.player_id, position=position)
        raise Exception("No valid moves available.")

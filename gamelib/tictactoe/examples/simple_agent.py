"""
Sample Tic-Tac-Toe Agent Implementation.
"""

from gamelib.tictactoe.agent import Agent


class TicTacToeAgent(Agent):
    def initialize(self):
        """
        Initialize the Tic-Tac-Toe agent before the game starts.
        """
        # No special initialization needed for this simple agent
        pass

    def get_move(self):
        """
        Decide on a move based on the current Tic-Tac-Toe game state.
        This simple agent selects the first available cell.
        """
        for position in range(9):
            if self.state.board[position] == -1:  # Check for empty cell
                return f'{{"player": {self.player_id}, "position": {position}}}'
        raise Exception("No valid moves available.")

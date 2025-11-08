"""
Tic Tac Toe game engine implementation.
"""

from gamelib.engine_base import EngineBase
from gamelib.tictactoe.gamestate import State
from gamelib.tictactoe.move import Move


class Engine(EngineBase):
    """
    Tic Tac Toe game engine implementation.
    """

    def validate_move(self, game_state: State, move: Move) -> bool:
        """
        Validate a move against the current game state.
        A move is valid if the position is within bounds and the cell is empty.
        """
        assert isinstance(game_state, State), "Invalid game state type."
        assert isinstance(move, Move), "Invalid move type."
        if not (0 <= move.position < 9):
            return False
        if game_state.board[move.position] != -1:
            return False
        if move.player != game_state.current_player:
            return False
        return True

    def apply_move(self, game_state: State, move: Move) -> State:
        """
        Apply a move to the game state and return the new game state.
        """
        if not self.validate_move(game_state, move):
            raise ValueError("Invalid move")

        new_state = game_state.clone()
        new_state.board[move.position] = move.player
        new_state.current_player = 1 - move.player  # Switch players

        self.status = self.get_winner(new_state)

        return new_state

    def get_winner(self, game_state: State) -> int:
        """
        Get the winner of the game.
        Returns:
            int: 0 if player 1 wins, 1 if player 2 wins, -1 for a draw, 0 if the game is ongoing.
        """
        winning_positions = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # columns
            [0, 4, 8], [2, 4, 6]              # diagonals
        ]
        for positions in winning_positions:
            if (game_state.board[positions[0]] != -1 and
                game_state.board[positions[0]] == game_state.board[positions[1]] == game_state.board[positions[2]]):
                return 1 if game_state.board[positions[0]] == 0 else 2  # Return the winning player

        if all(cell != -1 for cell in game_state.board):
            return -1  # Draw

        return 0  # Game is ongoing

    def is_game_over(self, game_state: State) -> bool:
        """
        Check if the game is over based on the current game state.
        The game is over if there is a winner or if the board is full.
        Returns:
            bool: True if the game is over, False otherwise.
        """
        return self.get_winner(game_state) != 0

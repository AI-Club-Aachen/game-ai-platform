"""
Tic Tac Toe game engine implementation.
"""

from typing import override

from gamelib.engine_base import EngineBase
from gamelib.tictactoe.gamestate import GameState as State
from gamelib.tictactoe.move import Move


class Engine(EngineBase):
    """
    Tic Tac Toe game engine implementation.
    """

    @override
    def __init__(self):
        """
        Initialize the game engine (no initialization needed).
        """
        pass

    @override
    def validate_move(self, game_state: State, move: Move) -> bool:
        """
        Validate a move against the current game state.
        A move is valid if the position is within bounds and the cell is empty.
        """
        if not isinstance(game_state, State):
            raise TypeError("Invalid game state type.")
        if not isinstance(move, Move):
            raise TypeError("Invalid move type.")
        if not (0 <= move.position < 9):
            return False
        if game_state.board[move.position] != -1:
            return False
        if move.player != game_state.turn:
            return False
        return True

    @override
    def apply_move(self, game_state: State, move: Move) -> State:
        """
        Apply a move to the game state and return the new game state.
        """
        if not self.validate_move(game_state, move):
            raise ValueError("Invalid move")

        new_state = game_state.clone()
        new_state.board[move.position] = move.player
        new_state.turn = 1 - move.player  # Switch players
        new_state.status = self.get_status(new_state)  # Update status

        return new_state

    @override
    def get_status(self, game_state: State) -> int:
        """
        Get the winner of the game.
        Returns:
            int: 0 if player 0 wins, 1 if player 1 wins, -2 for a draw, -1 if the game is ongoing.
        """
        status = None

        winning_positions = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # columns
            [0, 4, 8], [2, 4, 6]              # diagonals
        ]
        for positions in winning_positions:
            if (game_state.board[positions[0]] != -1 and
                game_state.board[positions[0]] == game_state.board[positions[1]] == game_state.board[positions[2]]):
                status = game_state.board[positions[0]]  # Return the winning player

        if all(cell != -1 for cell in game_state.board):
            status = -2  # Draw

        if status is None:
            status = -1  # Game is ongoing

        return status

    @override
    def is_game_over(self, game_state: State) -> bool:
        """
        Check if the game is over based on the current game state.
        The game is over if there is a winner or if the board is full.
        Warning: this method does not contain the actual logic, it relies on the status attribute of the game state.
        Returns:
            bool: True if the game is over, False otherwise.
        """
        return game_state.status != -1

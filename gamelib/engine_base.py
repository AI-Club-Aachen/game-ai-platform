"""
Base class for game engine implementations.
Provides common functionality and interfaces for different game engines.
"""

from gamelib.gamestate_base import GameStateBase
from gamelib.move_base import MoveBase


class EngineBase:
    """
    Base class for game engine implementations.
    Provides common functionality and interfaces for different game engines.
    To implement a game engine, subclass this EngineBase and override the methods below.
    Also implement state and move classes for the specific game.
    """

    def __init__(self):
        """
        Initialize the game engine.
        Sets the initial game status (0 = ongoing).
        """
        self.status = 0

    def validate_move(self, game_state: GameStateBase, move: MoveBase) -> bool:
        """
        Validate a move against the current game state.
        Subclasses must implement this.
        """
        raise NotImplementedError

    def apply_move(self, game_state: GameStateBase, move: MoveBase) -> GameStateBase:
        """
        Apply a move to the game state and return the new game state.
        Also updates game status if needed.
        Subclasses must implement this.
        """
        raise NotImplementedError

    def is_game_over(self, game_state: GameStateBase) -> bool:
        """
        Check if the game is over based on the current game state.
        Returns:
            bool: True if the game is over, False otherwise.
        Subclasses must implement this.
        """
        raise NotImplementedError

    def get_winner(self, game_state: GameStateBase) -> int:
        """
        Determine the winner of the game based on the current game state.
        Returns:
            int: integer representing the game state (e.g., 0 for ongoing, 1 for player 1 wins, 2 for player 2 wins, -1 for draw).
        Subclasses must implement this.
        """
        raise NotImplementedError

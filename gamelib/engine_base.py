"""
Base class for game engine implementations.
Provides common functionality and interfaces for different game engines.
"""

from gamelib.gamestate_base import GameStateBase
from gamelib.move_base import MoveBase


class EngineBase:
    """
    Base class for game engine implementations.
    """
    def __init__(self):
        """
        Initialize the game engine.
        """
        pass

    def validate_move(self, game_state: GameStateBase, move: MoveBase) -> bool:
        """
        Validate a move against the current game state.
        Subclasses must implement this.
        """
        raise NotImplementedError

    def apply_move(self, game_state: GameStateBase, move: MoveBase) -> GameStateBase:
        """
        Apply a move to the game state and return the new game state.
        Subclasses must implement this.
        """
        raise NotImplementedError

    def is_game_over(self, game_state: GameStateBase) -> int:
        """
        Check if the game is over based on the current game state.
        Returns:
            int: 0 if the game is ongoing, 1 if player 1 wins, 2 if player 2 wins, -1 for a draw.
        Subclasses must implement this.
        """
        raise NotImplementedError

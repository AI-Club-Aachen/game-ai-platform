"""
Base class for game engine implementations.
Provides common functionality and interfaces for different game engines.
"""

from abc import ABC, abstractmethod

from gamelib.gamestate_base import GameStateBase
from gamelib.move_base import MoveBase


class EngineBase(ABC):
    """
    Base class for game engine implementations.
    Provides common functionality and interfaces for different game engines.
    To implement a game engine, subclass this EngineBase and override the methods below.
    Also implement state and move classes for the specific game.
    The engine class is meant to be stateless; any game status should be derived from the game state.
    However, for effiency, some values may be cached as attributes.
    """

    @abstractmethod
    def __init__(self) -> None:
        """
        Initialize the game engine.
        """
        raise NotImplementedError

    @abstractmethod
    def validate_move(self, game_state: GameStateBase, move: MoveBase) -> bool:
        """
        Validate a move against the current game state.
        Subclasses must implement this.
        """
        raise NotImplementedError

    @abstractmethod
    def apply_move(self, game_state: GameStateBase, move: MoveBase) -> GameStateBase:
        """
        Apply a move to the game state and return the new game state.
        Also updates game status if needed.
        Subclasses must implement this.
        """
        raise NotImplementedError

    @abstractmethod
    def is_game_over(self, game_state: GameStateBase) -> bool:
        """
        Check if the game is over based on the current game state.
        Returns:
            bool: True if the game is over, False otherwise.
        Subclasses must implement this.
        """
        raise NotImplementedError

    @abstractmethod
    def get_status(self, game_state: GameStateBase) -> int:
        """
        Determine the status of the game based on the current game state.
        Returns:
            int: integer representing the game state
                (integers >= 0 represent player ids while -1 represents ongoing and < -1 represent other states such as draw).
        Subclasses must implement this.
        """
        raise NotImplementedError

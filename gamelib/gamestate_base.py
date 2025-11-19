"""
Base class for game state representations.
Provides common functionality and interfaces for different states in games.
"""

from abc import ABC, abstractmethod


class GameStateBase(ABC):
    """
    Base class for game state representations.
    """

    @classmethod
    @abstractmethod
    def initial(cls, init_data: dict = {}):
        """
        Initialize a game state from initialization data.
        This represents the starting state of the game.
        Subclasses must implement this.
        """
        raise NotImplementedError

    @abstractmethod
    def clone(self):
        """
        Return a deep copy of the game state.
        Subclasses must implement this.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_json(cls, json_str: str):
        """
        Initialize from JSON string.
        Subclasses must implement this.
        """
        raise NotImplementedError
    
    @abstractmethod
    def to_json(self) -> str:
        """
        Convert to a JSON string.
        Subclasses must implement this.
        """
        raise NotImplementedError

"""
Base class for move representations.
Provides common functionality and interfaces for different moves in games.
"""

from abc import ABC, abstractmethod


class MoveBase(ABC):
    """
    Base class for move representations.
    """

    @classmethod
    @abstractmethod
    def from_json(cls, json_str: str):
        """
        Initialize from a JSON string.
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

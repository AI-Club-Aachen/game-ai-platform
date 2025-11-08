"""
Base class for move representations.
Provides common functionality and interfaces for different moves in games.
"""

class MoveBase():
    """
    Base class for move representations.
    """

    @classmethod
    def from_json(cls, json_str: str):
        """
        Initialize from a JSON string.
        Subclasses must implement this.
        """
        raise NotImplementedError

    def to_json(self) -> str:
        """
        Convert to a JSON string.
        Subclasses must implement this.
        """
        raise NotImplementedError

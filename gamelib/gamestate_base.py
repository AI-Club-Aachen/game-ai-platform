"""
Base class for game state representations.
Provides common functionality and interfaces for different states in games.
"""

class GameStateBase():
    """
    Base class for game state representations.
    """

    def clone(self):
        """
        Return a deep copy of the game state.
        Subclasses must implement this.
        """
        raise NotImplementedError

    @classmethod
    def from_json(cls, json_str: str):
        """
        Initialize from JSON string.
        Subclasses must implement this.
        """
        raise NotImplementedError
    
    def to_json(self) -> str:
        """
        Convert to a JSON string.
        Subclasses must implement this.
        """
        raise NotImplementedError

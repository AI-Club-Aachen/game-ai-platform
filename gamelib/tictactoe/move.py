"""
Tic-Tac-Toe move representation.
"""

import json

from gamelib.move_base import MoveBase


class Move(MoveBase):
    """
    Tic-Tac-Toe move representation.
    """

    def __init__(self, player: int, position: int):
        self.player = player
        self.position = position

    @classmethod
    def from_json(cls, json_str: str):
        """
        Initialize the move from a JSON string.
        """
        json_data = json.loads(json_str)
        assert isinstance(json_data, dict) and "player" in json_data and "position" in json_data, "Invalid move format."
        move = cls(
            player=json_data.get("player"),
            position=json_data.get("position")
        )
        return move

    def to_json(self) -> str:
        """
        Convert the move to a JSON string.
        """
        return json.dumps({
            "position": self.position,
            "player": self.player
        })

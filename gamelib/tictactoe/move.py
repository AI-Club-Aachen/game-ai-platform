"""
Tic-Tac-Toe move representation.
"""

import json
from typing import override

from pydantic import BaseModel

from gamelib.move_base import MoveBase


class Move(BaseModel, MoveBase):
    """
    Tic-Tac-Toe move representation.
    """
    player: int
    position: int

    @classmethod
    @override
    def from_json(cls, json_str: str):
        """
        Initialize the move from a JSON string.
        """
        try:
            json_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding JSON string for move: {json_str}.") from e
        if not isinstance(json_data, dict):
            raise TypeError("Invalid move format: not a JSON object.")
        if not "player" in json_data:
            raise TypeError("Invalid move format: missing player attribute.")
        if not isinstance(json_data["player"], int):
            raise TypeError("Invalid move format in player: not an integer.")
        if not json_data["player"] in [0, 1]:
            raise ValueError("Invalid move format: player must be 0 or 1.")
        if not "position" in json_data:
            raise TypeError("Invalid move format: missing position attribute.")
        if not isinstance(json_data["position"], int):
            raise TypeError("Invalid move format in position: not an integer.")
        if not (0 <= json_data["position"] < 9):
            raise ValueError("Invalid move format: position must be between 0 and 8.")
        move = cls(
            player=json_data["player"],
            position=json_data["position"]
        )
        return move

    @override
    def to_json(self) -> str:
        """
        Convert the move to a JSON string.
        """
        return json.dumps({
            "position": self.position,
            "player": self.player
        })

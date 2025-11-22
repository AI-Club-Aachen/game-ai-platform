"""
Tic-Tac-Toe move representation.
"""

import json
from typing import override

from pydantic import BaseModel, field_validator

from gamelib.move_base import MoveBase


class Move(BaseModel, MoveBase):
    """
    Tic-Tac-Toe move representation.
    """
    player: int
    position: int

    @field_validator('player')
    @classmethod
    def validate_player(cls, v: int) -> int:
        if v not in [0, 1]:
            raise ValueError("Invalid move format: player must be 0 or 1.")
        return v

    @field_validator('position')
    @classmethod
    def validate_position(cls, v: int) -> int:
        if not (0 <= v < 9):
            raise ValueError("Invalid move format: position must be between 0 and 8.")
        return v

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
        
        return cls.model_validate(json_data)

    @override
    def to_json(self) -> str:
        """
        Convert the move to a JSON string.
        """
        return json.dumps({
            "position": self.position,
            "player": self.player
        })

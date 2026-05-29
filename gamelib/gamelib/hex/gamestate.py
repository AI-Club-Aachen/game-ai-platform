"""
Hex game state representation.
"""

import json
from typing import override

from pydantic import BaseModel, field_validator, model_validator

from gamelib.gamestate_base import GameStateBase


class GameState(BaseModel, GameStateBase):
    """
    Hex game state representation.

    A state is represented as a square grid where each cell can be:
        -1: empty
        0: player 0's mark (e.g., Red/Horizontal)
        1: player 1's mark (e.g., Blue/Vertical)

    Additionally, an integer that indicates which player's turn it is.
    """

    board_size: int
    board: list[list[int]]
    turn: int
    status: int

    @model_validator(mode="after")
    def validate_board_length(self):
        if len(self.board) != self.board_size:
            raise ValueError(f"Invalid game state format: board must have {self.board_size} rows.")
        for row in self.board:
            if len(row) != self.board_size:
                raise ValueError(f"Invalid game state format: board must have {self.board_size} columns in each row.")
        return self

    @field_validator("board")
    @classmethod
    def validate_board(cls, v: list[list[int]]) -> list[list[int]]:
        for row in v:
            for cell in row:
                if cell not in [-1, 0, 1]:
                    raise ValueError(f"Invalid game state format in board cell {cell}: must be -1, 0, or 1.")
        return v

    @field_validator("turn")
    @classmethod
    def validate_turn(cls, v: int) -> int:
        if v not in [0, 1]:
            raise ValueError("Invalid game state format: turn must be 0 or 1.")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: int) -> int:
        if v not in [-2, -1, 0, 1]:
            raise ValueError("Invalid game state format: status must be -2, -1, 0, or 1.")
        return v

    @override
    @classmethod
    def initial(cls, state_init_data: dict | None = None) -> "GameState":
        """
        Create the initial game state using the provided initialization data.
        In this case, the board is empty and the turn is set to player 0 unless specified in state_init_data.
        Args:
            state_init_data (dict): Initialization data for the game state (can contain "board_size", "turn", and "status").
        Returns:
            GameState: The initial game state.
        """
        if state_init_data is None:
            state_init_data = {}
        board_size = state_init_data.get("board_size", 11)  # 11 is standard Hex size
        board = [[-1] * board_size for _ in range(board_size)]  # Initialize an empty 2D board
        turn = state_init_data.get("turn", 0)  # Start with player 0 or provided turn
        status = state_init_data.get("status", -1)  # Game ongoing by default

        return cls(board_size=board_size, board=board, turn=turn, status=status)

    @override
    def clone(self) -> "GameState":
        """
        Return a deep copy of the game state.
        Returns:
            GameState: A deep copy of the current game state.
        """
        cloned_board = [row.copy() for row in self.board]
        return GameState(board_size=self.board_size, board=cloned_board, turn=self.turn, status=self.status)

    @override
    @classmethod
    def from_json(cls, json_str: str) -> "GameState":
        """
        Initialize the game state from a JSON string.
        Args:
            json_str (str): JSON string representing the game state.
        Returns:
            GameState: The initialized game state.
        """
        try:
            json_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding JSON string for game state: {json_str}.") from e

        return cls.model_validate(json_data)

    @override
    def to_json(self) -> str:
        """
        Convert the game state to a JSON string.
        Returns:
            str: JSON string representing the game state.
        """
        return json.dumps({"board_size": self.board_size, "board": self.board, "turn": self.turn, "status": self.status})

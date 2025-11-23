"""
Tic-Tac-Toe game state representation.
"""

import json
from typing import override

from pydantic import BaseModel, field_validator

from gamelib.gamestate_base import GameStateBase


class GameState(BaseModel, GameStateBase):
    """
    Tic-Tac-Toe game state representation.

    A state is represented as a 3x3 grid where each cell can be:
        -1: empty
        0: player 0's mark
        1: player 1's mark

    Additionally, an integer that indicates which player's turn it is.
    """

    board: list[int]
    turn: int
    status: int

    @field_validator("board")
    @classmethod
    def validate_board(cls, v: list[int]) -> list[int]:
        if len(v) != 9:
            raise ValueError("Invalid game state format: board must have 9 cells.")
        for cell in v:
            if cell not in [-1, 0, 1]:
                raise ValueError(
                    f"Invalid game state format in board cell {cell}: must be -1, 0, or 1."
                )
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
    def initial(cls, state_init_data: dict = {}):
        """
        Create the initial game state using the provided initialization data.
        In this case, the board is empty and the turn is set to player 0 unless specified in state_init_data.
        Args:
            state_init_data (dict): Initialization data for the game state (in this case "turn" and "status").
        Returns:
            GameState: The initial game state.
        """
        board = [-1] * 9  # Initialize an empty board
        turn = state_init_data.get("turn", 0)  # Start with player 0 or provided turn
        status = state_init_data.get("status", -1)  # Game ongoing by default

        state = cls(board=board, turn=turn, status=status)
        return state

    @override
    def clone(self):
        """
        Return a deep copy of the game state.
        Returns:
            GameState: A deep copy of the current game state.
        """
        new_state = GameState(board=self.board.copy(), turn=self.turn, status=self.status)
        return new_state

    @override
    @classmethod
    def from_json(cls, json_str: str):
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
        return json.dumps({"board": self.board, "turn": self.turn, "status": self.status})

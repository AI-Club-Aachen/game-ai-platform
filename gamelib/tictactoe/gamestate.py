"""
Tic-Tac-Toe game state representation.
"""

import json
from typing import override

from pydantic import BaseModel

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

    @override
    @classmethod
    def initial(cls, init_data: dict = {}):
        """
        Create the initial game state using the provided initialization data.
        In this case, the board is empty and the turn is set to player 0 unless specified in init_data.
        """
        board = [-1] * 9  # Initialize an empty board
        turn = init_data.get("turn", 0)  # Start with player 0 or provided turn
        status = init_data.get("status", -1)  # Game ongoing by default
        
        state = cls(board=board, turn=turn, status=status)
        return state

    @override
    def clone(self):
        """
        Return a deep copy of the game state.
        """
        new_state = GameState(board=self.board.copy(), turn=self.turn, status=self.status)
        return new_state

    @override
    @classmethod
    def from_json(cls, json_str: str):
        """
        Initialize the game state from a JSON string.
        """
        try:
            json_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding JSON string for game state: {json_str}.") from e
        if not isinstance(json_data, dict):
            raise TypeError("Invalid game state format: not a JSON object.")
        if not "board" in json_data:
            raise TypeError("Invalid game state format: missing board attribute.")
        if not "turn" in json_data:
            raise TypeError("Invalid game state format: missing turn attribute.")
        if not isinstance(json_data["board"], list):
            raise TypeError("Invalid game state format in board: not a list.")
        if not len(json_data["board"]) == 9:
            raise ValueError("Invalid game state format: board must have 9 cells.")
        for cell in json_data["board"]:
            if not isinstance(cell, int):
                raise TypeError(f"Invalid game state format in board cell {cell}: not an integer.")
            if cell not in [-1, 0, 1]:
                raise ValueError(f"Invalid game state format in board cell {cell}: must be -1, 0, or 1.")
        if not isinstance(json_data["turn"], int):
            raise TypeError("Invalid game state format in turn: not an integer.")
        if json_data["turn"] not in [0, 1]:
            raise ValueError("Invalid game state format: turn must be 0 or 1.")
        if not "status" in json_data:
            raise TypeError("Invalid game state format: missing status attribute.")
        if not isinstance(json_data["status"], int):
            raise TypeError("Invalid game state format in status: not an integer.")
        if json_data["status"] not in [-2, -1, 0, 1]:
            raise ValueError("Invalid game state format: status must be -2, -1, 0, or 1.")
        board = json_data["board"]
        turn = json_data["turn"]
        status = json_data["status"]
        state = cls(board=board, turn=turn, status=status)
        return state
    
    @override
    def to_json(self) -> str:
        """
        Convert the game state to a JSON string.
        """
        return json.dumps({
            "board": self.board,
            "turn": self.turn,
            "status": self.status
        })

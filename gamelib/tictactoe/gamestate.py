"""
Tic-Tac-Toe game state representation.
"""

import json

from gamelib.gamestate_base import GameStateBase


class State(GameStateBase):
    """
    Tic-Tac-Toe game state representation.
    
    A state is represented as a 3x3 grid where each cell can be:
        -1: empty
        0: player 0's mark
        1: player 1's mark

    Additionally, an integer that indicates which player's turn it is.
    """

    def __init__(self):
        self.board = [-1] * 9  # Initialize an empty board
        self.current_player = 0  # Start with player 0

    def clone(self):
        """
        Return a deep copy of the game state.
        """
        new_state = State()
        new_state.board = self.board.copy()
        new_state.current_player = self.current_player
        return new_state

    @classmethod
    def from_json(cls, json_str: str):
        """
        Initialize the game state from a JSON string.
        """
        json_data = json.loads(json_str)
        assert isinstance(json_data, dict) and "board" in json_data and "turn" in json_data, "Invalid game state format."
        assert isinstance(json_data["board"], list) and len(json_data["board"]) == 9, "Invalid game state format in board."
        assert isinstance(json_data["turn"], int), "Invalid game state format in turn."
        state = cls()
        state.board = json_data["board"]
        state.current_player = json_data["turn"]
        return state
    
    def to_json(self) -> str:
        """
        Convert the game state to a JSON string.
        """
        return json.dumps({
            "board": self.board,
            "turn": self.current_player
        })

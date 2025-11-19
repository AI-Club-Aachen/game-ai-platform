"""
Base Tic-Tac-Toe Agent Implementation.
"""

from typing import override

from gamelib.agent_base import AgentBase
from gamelib.tictactoe.gamestate import GameState as State


class Agent(AgentBase):
    """
    Base Tic-Tac-Toe Agent Implementation.
    Inherits from the generic AgentBase and implements Tic-Tac-Toe specific input reading.
    To implement a Tic-Tac-Toe agent, subclass this Agent class and override the initialize and get_move methods.
    Do not override __init__; use initialize() instead.
    """

    def __init__(self, run_init: bool = True):
        """
        Initialize the Tic-Tac-Toe agent.
        Args:
            run_init (bool): Whether to run the init loop.
        """
        if run_init:
            super().__init__()
    
    @override
    def _read_init(self) -> dict:
        """
        Reads initialization input for the agent.
        In this case, player id.
        """
        init_input = self._read_input()
        init_state = State.from_json(init_input)
        player_id = init_state.turn  # Assuming init input contains which player the agent is
        return {"player_id": player_id}

    @override
    def _read_state(self) -> State:
        """
        Reads the current Tic-Tac-Toe game state input for the agent.
        """
        state_input = self._read_input()
        state = State.from_json(state_input)
        return state

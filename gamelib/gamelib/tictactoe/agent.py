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

    @override
    def _read_init(self) -> dict:
        """
        Reads initialization input for the agent which is a dictionary.
        In this case, a "player_id" key indicates which player the agent is.
        This data will be passed to the initialize() method of the subclass.
        Returns:
            dict: Initialization data for the agent.
        """
        agent_init_data = self._read_input()
        assert isinstance(agent_init_data, dict), "Initialization input must be a dictionary."
        assert "player_id" in agent_init_data, "Initialization input must contain 'player_id' key."
        return agent_init_data

    @override
    def _read_state(self) -> State:
        """
        Reads the current Tic-Tac-Toe game state input for the agent.
        Returns:
            State: The current game state.
        """
        state_input = self._read_input()
        return State.from_json(state_input)

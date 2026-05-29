"""
Base Hex Agent Implementation.
"""

import json
from typing import override

from gamelib.agent_base import AgentBase
from gamelib.hex.gamestate import GameState as State


class Agent(AgentBase):
    """
    Base Hex Agent Implementation.
    """

    @override
    def _read_init(self) -> dict:
        """
        Reads initialization input for the agent which is a dictionary.
        Returns:
            dict: Initialization data for the agent.
        """
        agent_init_data = json.loads(self._read_input())
        assert isinstance(agent_init_data, dict), f"Initialization input must be a dictionary: {agent_init_data}"
        assert "player_id" in agent_init_data, f"Initialization input must contain 'player_id' key: {agent_init_data}"
        return agent_init_data

    @override
    def _read_state(self) -> State:
        """
        Reads the current Hex game state input for the agent.
        Returns:
            State: The current game state.
        """
        state_input = self._read_input()
        return State.from_json(state_input)

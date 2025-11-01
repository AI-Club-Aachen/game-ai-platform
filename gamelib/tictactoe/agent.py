"""
Base Tic-Tac-Toe Agent Implementation.
"""

from gamelib.agent_base import AgentBase
from gamelib.tictactoe.gamestate import State


class Agent(AgentBase):
    def __init__(self):
        super().__init__()
    
    def _read_init(self):
        """
        Reads initialization input for the agent.
        In this case, player id.
        """
        init_input = self._read_input()
        init_state = State.from_json(init_input)
        self.player_id = init_state.current_player  # Assuming init input contains which player the agent is

    def _read_state(self):
        """
        Reads the current Tic-Tac-Toe game state input for the agent.
        """
        state_input = self._read_input()
        cur_state = State.from_json(state_input)
        self.state = cur_state

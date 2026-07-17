from __future__ import annotations

from typing import override

from gamelib import DevRunnerBase
from gamelib.hex.agent import Agent
from gamelib.hex.engine import Engine, GameStatus
from gamelib.hex.gamestate import GameState as State
from gamelib.hex.move import Move


EXPECTED_AGENT_COUNT = 2


class DevRunner(DevRunnerBase):
    """
    Dev runner for Hex game.
    """

    @override
    def __init__(self, board_size: int = 11) -> None:
        self.agents: list[Agent] = []
        self.board_size = board_size

    @override
    def add_agent(self, agent: Agent) -> None:
        self.agents.append(agent)

    @override
    def start(self) -> None:
        """Run a local two-agent Hex match and print the progress."""

        if len(self.agents) != EXPECTED_AGENT_COUNT:
            raise ValueError("DevRunner requires exactly two agents.")

        engine = Engine()
        state = State.initial({"board_size": self.board_size})

        for player_id, agent in enumerate(self.agents):
            agent.initialize({"player_id": player_id})

        print("Starting Hex dev match: Player 0 (Left-Right) vs Player 1 (Top-Bottom)")
        self._print_state(state)

        while not engine.is_game_over(state):
            current_player = state.turn
            cur_agent: Agent = self.agents[current_player]

            move: Move = cur_agent.get_move(state)  # type: ignore
            if not engine.validate_move(state, move):
                print(f"Player {current_player} made an invalid move: {move}")
                print("Match ended due to invalid move.")
                print(f"Result: Player {1 - current_player} wins by opponent's invalid move.")
                return

            state = engine.apply_move(state, move)
            print(f"Player {current_player} plays position {move.position}")
            self._print_state(state)

        self._announce_result(state)

    def _print_state(self, state: State, spacing: int = 1) -> None:
        """Pretty-print the board for quick debugging."""
        symbols = {-1: ".", 0: "X", 1: "O"}
        size = state.board_size
        rows = []
        for r in range(size):
            row_str = " " * r # Indent for hex shape
            row = " ".join(symbols[state.board[r][c]] for c in range(size))
            rows.append(row_str + row)
        board_str = "\n".join(rows)
        for _ in range(spacing):
            print()
        print(board_str)
        for _ in range(spacing):
            print()

    def _announce_result(self, state: State) -> None:
        """Print the final outcome of the match."""
        if state.status == GameStatus.DRAW.value:
            print("Result: Draw")
        else:
            print(f"Result: Player {state.status} wins")

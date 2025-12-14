from __future__ import annotations

from typing import override

from gamelib import DevRunnerBase
from gamelib.tictactoe.engine import Engine
from gamelib.tictactoe.gamestate import GameState as State
from gamelib.tictactoe.move import Move


EXPECTED_AGENT_COUNT = 2
DRAW_STATUS = -2


class DevRunner(DevRunnerBase):
    """
    Dev runner for Tic-Tac-Toe game.
    """

    @override
    def start(self) -> None:
        """Run a local two-agent Tic-Tac-Toe match and print the progress."""

        if len(self.agents) != EXPECTED_AGENT_COUNT:
            raise ValueError("DevRunner requires exactly two agents.")

        engine = Engine()
        state = State.initial()

        # Initialize agents with their player IDs (0 and 1).
        for player_id, agent in enumerate(self.agents):
            agent.initialize({"player_id": player_id})

        print("Starting Tic-Tac-Toe dev match: Player 0 (X) vs Player 1 (O)")
        self._print_state(state)

        while not engine.is_game_over(state):
            current_player = state.turn
            agent = self.agents[current_player]

            move: Move = agent.get_move(state)
            if not engine.validate_move(state, move):
                raise ValueError(f"Invalid move from player {current_player}: {move}")

            state = engine.apply_move(state, move)
            print(f"Player {current_player} plays position {move.position}")
            self._print_state(state)

        self._announce_result(state)

    def _print_state(self, state: State, spacing: int = 1) -> None:
        """Pretty-print the board for quick debugging."""

        symbols = { -1: ".", 0: "X", 1: "O" }
        rows = []
        for idx in range(0, State.BOARD_SIZE, 3):
            row = " | ".join(symbols[cell] for cell in state.board[idx : idx + 3])
            rows.append(row)
        board_str = "\n---------\n".join(rows)
        for _ in range(spacing):
            print()
        print(board_str)
        for _ in range(spacing):
            print()

    def _announce_result(self, state: State) -> None:
        """Print the final outcome of the match."""

        if state.status == DRAW_STATUS:
            print("Result: Draw")
        else:
            print(f"Result: Player {state.status} wins")

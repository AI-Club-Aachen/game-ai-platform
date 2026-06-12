"""
Human-controlled Tic-Tac-Toe agent for local play.

Lets a person play against an AI agent from the terminal by typing moves.
A HumanAgent is just another agent from the DevRunner's perspective, so no
changes to the DevRunner are needed.

Example usage:
    # Human (player 0) vs AI (player 1)
    from gamelib.tictactoe import DevRunner, HumanAgent
    from my_agent import MyAgent

    runner = DevRunner()
    runner.add_agent(HumanAgent())   # player 0
    runner.add_agent(MyAgent())      # player 1
    runner.start()
"""

from typing import ClassVar, NoReturn, override

from gamelib.tictactoe.agent import Agent
from gamelib.tictactoe.gamestate import GameState as State
from gamelib.tictactoe.move import Move


class HumanAgent(Agent):
    """
    A Tic-Tac-Toe agent driven by human keyboard input.

    Only ``initialize`` and ``get_move`` are meaningful. The stdin/stdout
    competition hooks inherited from ``AgentBase`` are disabled, because a
    HumanAgent is only ever driven through a local ``DevRunner``.
    """

    SYMBOLS: ClassVar[dict[int, str]] = {-1: ".", 0: "X", 1: "O"}

    @override
    def initialize(self, agent_init_data: dict) -> None:
        """Store which player slot (0 or 1) this human controls."""
        self.player_id = agent_init_data["player_id"]

    @override
    def get_move(self, game_state: State) -> Move:
        """Prompt the human for a move until a valid one is entered."""
        self._print_labeled_board(game_state)

        while True:
            try:
                raw = input("Your move (position 0–8): ")  # noqa: RUF001
            except (KeyboardInterrupt, EOFError):
                print("\nMatch aborted.")
                raise SystemExit(0) from None

            try:
                position = int(raw.strip())
            except ValueError:
                print(f"Invalid input {raw.strip()!r}: please enter a single integer 0–8.")  # noqa: RUF001
                continue

            try:
                move = Move(player=self.player_id, position=position)
            except ValueError as exc:
                print(f"Invalid move: {exc}")
                continue

            if game_state.board[position] != -1:
                print(f"Cell {position} is already taken; choose an empty cell.")
                continue

            return move

    def _print_labeled_board(self, state: State) -> None:
        """
        Print the board with position numbers shown in empty cells so the
        human can read off the index to play.
        """
        cells = [
            self.SYMBOLS[cell] if cell != -1 else str(idx)
            for idx, cell in enumerate(state.board)
        ]
        rows = [" | ".join(cells[idx : idx + 3]) for idx in range(0, State.BOARD_SIZE, 3)]
        board_str = "\n---------\n".join(rows)
        print()
        print(f"You are Player {self.player_id} ({self.SYMBOLS[self.player_id]})")
        print(board_str)
        print()

    # --- Competition-only hooks: disabled for human play -------------------

    @override
    def start(self) -> NoReturn:
        raise NotImplementedError("HumanAgent reads from stdin via DevRunner; do not call agent.start().")

    @override
    def _read_init(self) -> NoReturn:
        raise NotImplementedError("HumanAgent is initialized by DevRunner; _read_init is not used.")

    @override
    def _read_state(self) -> NoReturn:
        raise NotImplementedError("HumanAgent receives state from DevRunner; _read_state is not used.")

    @override
    def _write_output(self, output: str) -> NoReturn:
        raise NotImplementedError("HumanAgent returns moves directly; _write_output is not used.")

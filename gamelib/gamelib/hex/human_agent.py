"""
Human-controlled Hex agent for local play.

Lets a person play against an AI agent from the terminal by typing moves.
A HumanAgent is just another agent from the DevRunner's perspective, so no
changes to the DevRunner are needed.

Example usage:
    # Human (player 0) vs AI (player 1)
    from gamelib.hex import DevRunner, HumanAgent
    from my_agent import MyAgent

    runner = DevRunner()
    runner.add_agent(HumanAgent())   # player 0
    runner.add_agent(MyAgent())      # player 1
    runner.start()
"""

from typing import ClassVar, NoReturn, override

from gamelib.hex.agent import Agent
from gamelib.hex.gamestate import GameState as State
from gamelib.hex.move import Move


# Boards up to this size show a "row,col" shorthand inside empty cells.
SHORTHAND_MAX_SIZE = 5

# A Hex move is entered as two comma-separated coordinates (row, col).
EXPECTED_COORD_COUNT = 2


class HumanAgent(Agent):
    """
    A Hex agent driven by human keyboard input.

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

        size = game_state.board_size
        while True:
            try:
                raw = input("Your move (row,col e.g. 3,4): ")
            except (KeyboardInterrupt, EOFError):
                print("\nMatch aborted.")
                raise SystemExit(0) from None

            parts = raw.strip().replace(" ", "").split(",")
            if len(parts) != EXPECTED_COORD_COUNT:
                print(f"Invalid input {raw.strip()!r}: expected two comma-separated integers, e.g. 3,4.")
                continue

            try:
                row, col = int(parts[0]), int(parts[1])
            except ValueError:
                print(f"Invalid input {raw.strip()!r}: row and col must be integers.")
                continue

            try:
                move = Move(player=self.player_id, position=[row, col])
            except ValueError as exc:
                print(f"Invalid move: {exc}")
                continue

            if not (0 <= row < size and 0 <= col < size):
                print(f"Position ({row},{col}) is off the {size}x{size} board.")
                continue

            if game_state.board[row][col] != -1:
                print(f"Cell ({row},{col}) is already taken; choose an empty cell.")
                continue

            return move

    def _print_labeled_board(self, state: State) -> None:
        """
        Print the board in its diagonal (rhombus) hex shape, with row indices
        on the left and column indices along the top so coordinates can be read
        off. Each row label travels with the row's indent, so it stays next to
        that row's first cell. The column header is aligned over the top row.

        For small boards, empty cells show the ``row,col`` shorthand; larger
        boards keep a simple ``.``.
        """
        size = state.board_size
        shorthand = size <= SHORTHAND_MAX_SIZE

        # Fixed column width that fits the widest cell content and the headers.
        label_w = len(str(size - 1))
        content_w = len(f"{size - 1},{size - 1}") if shorthand else 1
        cell_w = max(label_w, content_w)
        # Half-cell offset per row reproduces the slanted hex board.
        indent_unit = (cell_w + 1) // 2

        def cell_text(r: int, c: int) -> str:
            value = state.board[r][c]
            if value != -1:
                return self.SYMBOLS[value]
            return f"{r},{c}" if shorthand else "."

        print()
        print(f"You are Player {self.player_id} ({self.SYMBOLS[self.player_id]})")

        header = " " * (label_w + 1) + " ".join(f"{c:>{cell_w}}" for c in range(size))
        print(header)
        for r in range(size):
            indent = " " * (indent_unit * r)
            cells = " ".join(f"{cell_text(r, c):>{cell_w}}" for c in range(size))
            print(f"{indent}{r:>{label_w}} {cells}")
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

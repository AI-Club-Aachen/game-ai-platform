from enum import Enum
from typing import Any


class GameType(str, Enum):
    """
    Strongly typed enum for supported games.
    Each game type has associated metadata accessible via properties.
    """

    TICTACTOE = "tictactoe"
    CHESS = "chess"
    CONNECT_FOUR = "connect_four"
    HEX = "hex"

    @property
    def display_name(self) -> str:
        """Human-readable display name for the game."""
        names = {
            GameType.TICTACTOE: "Tic-Tac-Toe",
            GameType.CHESS: "Chess",
            GameType.CONNECT_FOUR: "Connect Four",
            GameType.HEX: "Hex",
        }
        return names[self]

    @property
    def description(self) -> str:
        """Description of the game."""
        descriptions = {
            GameType.TICTACTOE: "Classic 3x3 grid game. Get three in a row to win!",
            GameType.CHESS: "The timeless strategy game of kings and queens.",
            GameType.CONNECT_FOUR: "Drop discs to connect four in a row, column, or diagonal.",
            GameType.HEX: "A connection strategy game played on a hexagonal grid.",
        }
        return descriptions[self]

    @property
    def icon(self) -> str:
        """Icon identifier for the game (can be emoji or icon library reference)."""
        icons = {
            GameType.TICTACTOE: "⭕",
            GameType.CHESS: "♟️",
            GameType.CONNECT_FOUR: "🔴",
            GameType.HEX: "🛑",
        }
        return icons[self]

    @property
    def min_players(self) -> int:
        """Minimum number of players required."""
        return 2

    @property
    def max_players(self) -> int:
        """Maximum number of players allowed."""
        return 2

    @property
    def is_turn_based(self) -> bool:
        """Whether the game is turn-based."""
        return True

    @property
    def additional_data(self) -> dict[str, Any]:
        """Additional data specific to the game."""
        data = {
            # 11 is the standard Hex size and matches the gamelib engine default.
            GameType.HEX: {"board_size": 11},
        }
        return data.get(self, {})

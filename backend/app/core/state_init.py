"""Per-game whitelist validation for match ``state_init_data`` (M-10).

User-controlled ``state_init_data`` from ``POST /matches`` is passed straight to
``State.initial(...)`` inside the privileged match worker (it holds the Docker
socket and worker API key, and is not itself sandboxed). The agent *code* runs in
a hardened container, but engine/state initialization does not — so this input is
treated as untrusted and validated against an explicit per-game-type whitelist of
allowed keys, types, and numeric bounds before a match is queued.
"""

from typing import Any

from app.core.config import settings
from app.models.game import GameType


# turn/status values are fixed by the gamelib engines (gamelib/<game>/gamestate.py).
_ALLOWED_TURN: tuple[int, ...] = (0, 1)
_ALLOWED_STATUS: tuple[int, ...] = (-2, -1, 0, 1)

# Whitelisted state_init_data keys per game. Games without a defined init schema
# (or not yet implemented) accept no keys at all.
_ALLOWED_KEYS: dict[GameType, frozenset[str]] = {
    GameType.TICTACTOE: frozenset({"turn", "status"}),
    GameType.HEX: frozenset({"board_size", "turn", "status"}),
    GameType.CHESS: frozenset(),
    GameType.CONNECT_FOUR: frozenset(),
}


class StateInitValidationError(ValueError):
    """Raised when ``state_init_data`` fails per-game whitelist validation (M-10)."""


def _require_int(key: str, value: Any) -> int:
    # bool is an int subclass; reject it so "turn": true cannot slip through.
    if not isinstance(value, int) or isinstance(value, bool):
        raise StateInitValidationError(f"state_init_data.{key} must be an integer")
    return value


def _check_enum(key: str, value: Any, allowed: tuple[int, ...]) -> None:
    if _require_int(key, value) not in allowed:
        raise StateInitValidationError(f"state_init_data.{key} must be one of {list(allowed)}")


def _check_board_size(value: Any) -> None:
    size = _require_int("board_size", value)
    max_size = settings.MAX_HEX_BOARD_SIZE
    if not (2 <= size <= max_size):  # noqa: PLR2004
        raise StateInitValidationError(f"state_init_data.board_size must be between 2 and {max_size}")


def validate_state_init_data(game_type: GameType, data: dict[str, Any]) -> None:
    """Validate ``state_init_data`` for a game type or raise ``StateInitValidationError``.

    Rejects non-dict payloads, keys outside the per-game whitelist, wrong types,
    and out-of-range numeric values.
    """
    if not isinstance(data, dict):
        raise StateInitValidationError("state_init_data must be an object")

    allowed = _ALLOWED_KEYS.get(game_type, frozenset())
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise StateInitValidationError(
            f"state_init_data contains unsupported keys for '{game_type.value}': {unknown}"
        )

    for key, value in data.items():
        if key == "board_size":
            _check_board_size(value)
        elif key == "turn":
            _check_enum("turn", value, _ALLOWED_TURN)
        elif key == "status":
            _check_enum("status", value, _ALLOWED_STATUS)

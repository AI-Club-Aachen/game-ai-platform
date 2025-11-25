# Game Library (`gamelib`)

This directory contains the core game logic and interfaces for the AI Game Competition Platform. It is designed to be modular and extensible, allowing for easy addition of new games.

## Structure

- **Base Classes**: The root of `gamelib` contains abstract base classes that define the standard interface for all games.
    - `agent_base.py`: Base class for AI agents.
    - `engine_base.py`: Base class for game engines (rules, move validation, state updates).
    - `gamestate_base.py`: Base class for game state representations.
    - `move_base.py`: Base class for move representations.

- **Game Implementations**: Each game has its own subdirectory (e.g., `tictactoe/`) containing implementations of the base classes.
    - `gamestate.py`: Defines the specific game state (board, scores, etc.).
    - `move.py`: Defines valid moves for the game.
    - `engine.py`: Implements the game rules.
    - `agent.py`: Base agent for the specific game (handles game-specific I/O).

- **Tests**: `tests/` contains unit and integration tests for the games.

## Implementing a New Game

To add a new game (e.g., "Chess"), follow these steps:

1.  **Create a Directory**: Create `gamelib/chess/`.
2.  **Implement State**: Create `gamelib/chess/gamestate.py` inheriting from `GameStateBase`. Implement `initial`, `clone`, `from_json`, and `to_json`.
3.  **Implement Move**: Create `gamelib/chess/move.py` inheriting from `MoveBase`. Implement `from_json` and `to_json`.
4.  **Implement Engine**: Create `gamelib/chess/engine.py` inheriting from `EngineBase`. Implement `validate_move`, `apply_move`, `is_game_over`, and `get_status`.
5.  **Implement Agent**: Create `gamelib/chess/agent.py` inheriting from `AgentBase`. Override `_read_init` and `_read_state` to parse your specific JSON formats.

## Tic-Tac-Toe Example

The `tictactoe/` directory provides a complete reference implementation.

- **State**: 3x3 board, current turn, and game status.
- **Engine**: Standard Tic-Tac-Toe rules.
- **Agent**: Includes a `SimpleAgent` example that plays random valid moves.

## Running Tests

Run the tests using pytest:

```bash
pytest gamelib/tests
```
or if multiple Python versions are installed:
```bash
py -3.12 -m pytest gamelib/tests
```

## Run linter, formatter and typecheck
After `uv sync`, you can run either:
```
uv run python -m scripts.commands lint
uv run python -m scripts.commands format
uv run python -m scripts.commands type-check
```
or with the venv activated:
```
python -m scripts.commands lint
python -m scripts.commands format
python -m scripts.commands type-check
```

## Packaging and Publishing
This package is published to PyPI using uv:
```
uv build
uv publish
```
Old builds must be manually deleted from the `dist/` folder before publishing again.

Publishing is done in a GitHub Action on release or manually.

It is also possible to publish using a PyPi API token:
```
uv publish --token <TOKEN>
```

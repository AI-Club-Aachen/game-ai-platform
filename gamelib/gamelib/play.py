"""
Local play entry point for gamelib.

Run a game in your terminal with no backend — human vs agent, agent vs agent,
or human vs human (hot-seat). After installing the package, use the console
script::

    gamelib-play <game> <player0> <player1>

``<game>`` is ``tictactoe`` or ``hex``. Each player is either the literal word
``human`` or a path to a Python file that defines an ``Agent`` subclass
(optionally ``path.py:ClassName`` to pick a specific class).

Examples::

    gamelib-play tictactoe human my_agent.py     # you move first, agent second
    gamelib-play hex my_agent.py human            # agent moves first, you second
    gamelib-play hex agent_a.py agent_b.py        # watch two agents play
    gamelib-play tictactoe human human            # two humans, hot-seat

Without installing the script you can equivalently run::

    python -m gamelib.play hex human my_agent.py
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any


# Game name -> import path of its package (which exports Agent/DevRunner/HumanAgent).
GAME_MODULES: dict[str, str] = {
    "tictactoe": "gamelib.tictactoe",
    "hex": "gamelib.hex",
}

# Sentinel a player spec uses to request an interactive human player.
HUMAN = "human"


def _load_agent_class(spec: str, base_cls: type) -> type:
    """
    Load an ``Agent`` subclass from ``path/to/file.py`` or
    ``path/to/file.py:ClassName``.

    If no class name is given, the single ``Agent`` subclass defined in the
    file is used; ambiguity raises with a helpful message.
    """
    path_part, _, class_name = spec.partition(":")
    path = Path(path_part).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"Agent file not found: {path}")

    module_spec = importlib.util.spec_from_file_location(path.stem, path)
    if module_spec is None or module_spec.loader is None:
        raise SystemExit(f"Could not load an agent module from {path}")

    module = importlib.util.module_from_spec(module_spec)
    try:
        module_spec.loader.exec_module(module)
    except Exception as exc:
        raise SystemExit(f"Failed to import {path}: {exc}") from exc

    if class_name:
        obj = getattr(module, class_name, None)
        if not (isinstance(obj, type) and issubclass(obj, base_cls)):
            raise SystemExit(f"{class_name!r} in {path} is not an Agent subclass.")
        return obj

    candidates = [
        obj
        for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, base_cls) and obj is not base_cls and obj.__module__ == module.__name__
    ]
    if not candidates:
        raise SystemExit(f"No Agent subclass found in {path}.")
    if len(candidates) > 1:
        names = ", ".join(sorted(c.__name__ for c in candidates))
        raise SystemExit(
            f"Multiple Agent subclasses found in {path} ({names}); "
            f"pick one with '{path.name}:ClassName'."
        )
    return candidates[0]


def _build_runner(game: str, player0: str, player1: str) -> tuple[Any, list[str]]:
    """Construct a DevRunner for the chosen game and add both players."""
    module = importlib.import_module(GAME_MODULES[game])
    agent_base = module.Agent
    human_cls = module.HumanAgent
    runner = module.DevRunner()

    labels: list[str] = []
    for spec in (player0, player1):
        if spec == HUMAN:
            runner.add_agent(human_cls())
            labels.append("Human")
        else:
            agent_cls = _load_agent_class(spec, agent_base)
            runner.add_agent(agent_cls())
            labels.append(agent_cls.__name__)
    return runner, labels


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for local play."""
    parser = argparse.ArgumentParser(
        prog="gamelib-play",
        description="Play a gamelib game locally: human vs agent, agent vs agent, or hot-seat.",
    )
    parser.add_argument("game", choices=sorted(GAME_MODULES), help="Which game to play.")
    parser.add_argument(
        "player0",
        help="Player 0: 'human' or a path to an agent .py file (optionally file.py:ClassName).",
    )
    parser.add_argument(
        "player1",
        help="Player 1: 'human' or a path to an agent .py file (optionally file.py:ClassName).",
    )
    args = parser.parse_args(argv)

    runner, labels = _build_runner(args.game, args.player0, args.player1)
    print(f"Local {args.game} match — Player 0: {labels[0]} vs Player 1: {labels[1]}\n")
    runner.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())

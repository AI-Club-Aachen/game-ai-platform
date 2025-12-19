# AICA Game Library

This package contains the core game logic and interfaces for the Game AI Competition Platform of the AI Club Aachen.
It is designed to be easy to use.
Simply instantiate the Agent class and begin!

## Installation

You can install the package via pip:

```bash
pip install aica-gamelib
```

## Creating an Agent

To create a game AI agent, you need to create a class that inherits from `gamelib.GAME.agent.Agent`.
`GAME` is replaced by the relevant game such as `tictactoe`.
You must implement two methods:
1. `initialize(self, agent_init_data)`: Setup your agent (e.g., store your player ID).
2. `get_move(self, game_state)`: Analyze the game state and return a `Move` object.

## Game Concepts

### GameState
The `GameState` object passed to `get_move` is defined in `gamelib.GAME.gamestate`.

### Move
The `Move` object returned by `get_move` is defined in `gamelib.GAME.move`.

## Example in TicTacToe

Here is a simple example of a tictactoe agent that selects the first available cell on the board.

```python
from typing import override

from gamelib.tictactoe import Agent, GameState, Move

class MyTicTacToeAgent(Agent):
    @override
    def initialize(self, agent_init_data: dict) -> None:
        """
        Called once at the start of the game.
        agent_init_data contains 'player_id' (0 or 1).
        """
        self.player_id = agent_init_data["player_id"]

    @override
    def get_move(self, game_state: GameState) -> Move:
        """
        Called every turn. Returns the move you want to make.
        """
        # The board is a flat list of 9 integers
        # -1: Empty, 0: Player 0, 1: Player 1
        for position in range(9):
            if game_state.board[position] == -1:
                return Move(player=self.player_id, position=position)
        
        raise ValueError("No valid moves available.")

if __name__ == "__main__":
    # Instantiate and start the agent (run by the platform)
    agent = MyTicTacToeAgent()
    agent.start()
```

You can import this example agent right away with:
```python
from gamelib.tictactoe.examples import TicTacToeAgent
```

## Running Your Agent

The agent uses standard input/output (stdin/stdout) to communicate with the game engine, when running on the platform. This is handled automatically as long as your agent is a subclass of `gamelib.GAME.agent.Agent`and properly started in the `__main__` block.

To test locally, you can use the DevRunner provided in the `gamelib.GAME.dev_runner` module:
```python
from gamelib.tictactoe import DevRunner

runner = DevRunner()
agent1 = TicTacToeAgent()
agent2 = TicTacToeAgent()
runner.add_agent(agent1)
runner.add_agent(agent2)
runner.start()
```

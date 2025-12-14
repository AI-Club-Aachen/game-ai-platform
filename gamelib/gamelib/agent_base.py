"""
Base class for game agent implementations.
Provides common functionality and interfaces for different game agents.
"""

from abc import ABC, abstractmethod

from gamelib.gamestate_base import GameStateBase as State
from gamelib.move_base import MoveBase as Move


class AgentBase(ABC):
    """
    Base class for game agent implementations.
    """

    def start(self) -> None:
        """
        Initialize the agent and start the game loop.
        Should only be used by competition servers.
        Use DevRunner for local testing instead.
        """
        init_data = self._read_init()
        self.initialize(init_data)
        while True:
            state: State = self._read_state()
            move: Move = self.get_move(state)
            self._write_output(move.to_json())

    def _read_input(self) -> str:
        """
        Reads input from stdin
        """
        try:
            return input()
        except EOFError as eof:
            raise SystemExit(eof) from None

    def _write_output(self, output: str) -> None:
        """
        Writes output to stdout
        """
        print(output, flush=True)

    @abstractmethod
    def _read_init(self) -> dict:
        """
        Reads initialization input for the agent and returns it as a dictionary.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def initialize(self, agent_init_data: dict) -> None:
        """
        Initialize the agent before the game starts.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def _read_state(self) -> State:
        """
        Reads the current game state input for the agent and returns it as a State object.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def get_move(self, game_state: State) -> Move:
        """
        Decide on a move based on the given game state.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

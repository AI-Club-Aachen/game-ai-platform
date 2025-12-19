from abc import ABC, abstractmethod

from gamelib.agent_base import AgentBase


class DevRunnerBase(ABC):
    @abstractmethod
    def __init__(self) -> None:
        """
        Initialize the development runner.
        Subclasses must implement this.
        """
        raise NotImplementedError

    @abstractmethod
    def add_agent(self, agent: AgentBase) -> None:
        """
        Add an agent to the game.
        Subclasses must implement this.
        """
        raise NotImplementedError

    @abstractmethod
    def start(self) -> None:
        """
        Start the game loop.
        Subclasses must implement this.
        """
        raise NotImplementedError

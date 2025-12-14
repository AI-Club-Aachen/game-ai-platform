from abc import ABC, abstractmethod

from gamelib.agent_base import AgentBase


class DevRunnerBase(ABC):
    def __init__(self) -> None:
        self.agents: list[AgentBase] = []

    def add_agent(self, agent: AgentBase) -> None:
        self.agents.append(agent)

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError("This method should be overridden by subclasses.")

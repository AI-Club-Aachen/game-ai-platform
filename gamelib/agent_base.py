"""
Base class for game agent implementations.
Provides common functionality and interfaces for different game agents.
"""

class AgentBase():
    def __init__(self):
        """
        Initialize the agent and game loop.
        """
        self._read_init()
        self.initialize()
        while True:
            self._read_state()
            move = self.get_move()
            print(move)

    def _read_input(self):
        """
        Reads input from stdin
        """
        try:
            return input()
        except EOFError as eof:
            raise SystemExit(eof)

    def _read_init(self):
        """
        Reads initialization input for the agent.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    def initialize(self):
        """
        Initialize the agent before the game starts.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    def _read_state(self):
        """
        Reads the current game state input for the agent.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

    def get_move(self):
        """
        Decide on a move based on the current game state.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

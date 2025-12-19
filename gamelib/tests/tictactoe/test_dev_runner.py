"""
Test suite for TicTacToe DevRRunner.
"""

import sys
from io import StringIO

from gamelib.tictactoe.dev_runner import DevRunner
from gamelib.tictactoe.examples.simple_agent import TicTacToeAgent as Agent


def test_dev_runner():
    """
    Run the DevRunner with two simple agents and ensure a game completes.
    The printed outputs are also checked.
    """
    agent1 = Agent()
    agent2 = Agent()
    runner = DevRunner()
    runner.add_agent(agent1)
    runner.add_agent(agent2)

    # Capture printed output
    captured_output = StringIO()
    sys.stdout = captured_output

    runner.start()

    sys.stdout = sys.__stdout__
    output = captured_output.getvalue()

    assert "Starting Tic-Tac-Toe dev match" in output, "Match did not start correctly."
    assert "Player 0 plays position" in output, "Player 0 moves not printed."
    assert "Player 1 plays position" in output, "Player 1 moves not printed."
    assert "Result:" in output, "Match result not announced."

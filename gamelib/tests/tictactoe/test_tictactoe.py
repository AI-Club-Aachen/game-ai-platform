"""
Test suite for full game scenarios in gamelib.
"""

from gamelib.tictactoe.engine import Engine
from gamelib.tictactoe.gamestate import State
from gamelib.tictactoe.move import Move
from gamelib.tictactoe.examples.simple_agent import TicTacToeAgent


def test_validate_move():
    """
    Test the validate_move method of the TicTacToe engine.
    """
    engine = Engine()
    state = State()
    valid_move = Move(player=0, position=0)
    invalid_move_out_of_bounds = Move(player=0, position=9)
    invalid_move_occupied = Move(player=0, position=0)

    assert engine.validate_move(state, valid_move) == True, "Move should be valid."
    state.board[0] = 0  # Occupy position 0
    assert engine.validate_move(state, invalid_move_occupied) == False, "Move should be invalid (occupied)."
    assert engine.validate_move(state, invalid_move_out_of_bounds) == False, "Move should be invalid (out of bounds)."


def test_full_game():
    """
    Test a full game of Tic-Tac-Toe between two simple agents.
    """
    agent1 = TicTacToeAgent(run_init=False)
    agent1.player_id = 0
    agent2 = TicTacToeAgent(run_init=False)
    agent2.player_id = 1
    engine = Engine()
    assert engine.status == 0, "Initial game status should be ongoing (0)."
    state = State()  # Initial empty state

    while not engine.is_game_over(state):
        assert engine.status == 0, "Game should be ongoing."

        if state.current_player == 0:
            move = agent1.get_move(state)
        else:
            move = agent2.get_move(state)

        assert engine.validate_move(state, move), f"Move {move} should be valid."
        state = engine.apply_move(state, move)

    assert engine.status != 0, "Game should be over."
    result = engine.get_winner(state)
    assert result == 1, "Player 1 should win the game."
    assert result != 2, "Player 2 should not win the game."
    assert result != -1, "The game should not end in a draw."


def test_serialization():
    """
    Test serialization and deserialization of game state and moves.
    """
    state = State()
    move = Move(player=0, position=4)

    state_json = state.to_json()
    move_json = move.to_json()

    restored_state = State.from_json(state_json)
    restored_move = Move.from_json(move_json)

    assert state.board == restored_state.board, "Restored state board should match original."
    assert state.current_player == restored_state.current_player, "Restored state current player should match original."
    assert move.player == restored_move.player, "Restored move player should match original."
    assert move.position == restored_move.position, "Restored move position should match original."

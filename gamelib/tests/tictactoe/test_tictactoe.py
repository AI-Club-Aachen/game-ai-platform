"""
Test suite for full game scenarios in gamelib.
"""

import pytest
from pydantic import ValidationError

from gamelib.tictactoe.engine import Engine
from gamelib.tictactoe.examples.simple_agent import TicTacToeAgent as Agent
from gamelib.tictactoe.gamestate import GameState as State
from gamelib.tictactoe.move import Move


def test_validate_move():
    """
    Test the validate_move method of the TicTacToe engine.
    """
    engine = Engine()
    state = State.initial()
    move = Move(player=0, position=0)
    with pytest.raises(ValidationError):
        _ = Move(player=0, position=9)

    assert engine.validate_move(state, move) == True, "Move should be valid."
    state.board[0] = 0  # Occupy position 0
    assert engine.validate_move(state, move) == False, "Move should be invalid (occupied)."


def test_full_game():
    """
    Test a full game of Tic-Tac-Toe between two simple agents.
    """
    agent1 = Agent(run_init=False)
    agent1.player_id = 0
    agent2 = Agent(run_init=False)
    agent2.player_id = 1
    engine = Engine()
    state = State.initial()  # Initial empty state
    assert state.turn == 0, "Initial turn should be player 0."
    assert state.status == -1, "Initial game status should be ongoing (-1)."

    while not engine.is_game_over(state):
        assert state.status == -1, "Game should be ongoing."
        if state.turn == 0:
            move = agent1.get_move(state)
        else:
            move = agent2.get_move(state)

        assert engine.validate_move(state, move), f"Move {move} should be valid."
        state = engine.apply_move(state, move)

    assert state.status != -1, "Game should be over."
    assert state.status == 0, "Player 0 should win the game."


def test_serialization():
    """
    Test serialization and deserialization of game state and moves.
    """
    state = State.initial({"turn": 1})
    cloned_state = state.clone()
    assert state.board == cloned_state.board, "Cloned state board should match original."
    assert state.turn == cloned_state.turn, "Cloned state turn should match original."
    move = Move(player=0, position=4)

    state_json = state.to_json()
    cloned_state_json = cloned_state.to_json()
    assert state_json == cloned_state_json, "Serialized JSON of cloned state should match original."
    move_json = move.to_json()

    restored_state = State.from_json(state_json)
    restored_move = Move.from_json(move_json)

    assert state.board == restored_state.board, "Restored state board should match original."
    assert state.turn == restored_state.turn, "Restored state current player should match original."
    assert move.player == restored_move.player, "Restored move player should match original."
    assert move.position == restored_move.position, "Restored move position should match original."


def test_win_on_last_move():
    """
    Test that a win on the very last move is correctly identified as a win, not a draw.
    """
    engine = Engine()
    # Board setup:
    # X O X
    # X O O
    # . X O
    # Player 0 (X) plays at position 6 (bottom-left) to win.
    board = [0, 1, 0, 0, 1, 1, -1, 0, 1]
    state = State(board=board, turn=0, status=-1)
    move = Move(player=0, position=6)

    new_state = engine.apply_move(state, move)

    assert new_state.status == 0, "Player 0 should win on the last move."
    assert new_state.board[6] == 0, "Board should be updated."
    assert engine.is_game_over(new_state), "Game should be over."


def test_draw_on_last_move():
    """
    Test that a draw on the very last move is correctly identified as a draw.
    """
    engine = Engine()
    # Board setup for a draw:
    # X O X
    # X O O
    # . X X
    # Player 1 (O) plays at position 6 (bottom-left).
    # Result:
    # X O X
    # X O O
    # O X X
    # No winner, board full -> Draw.
    board = [0, 1, 0, 0, 1, 1, -1, 0, 0]
    state = State(board=board, turn=1, status=-1)
    move = Move(player=1, position=6)

    new_state = engine.apply_move(state, move)

    assert new_state.status == -2, "Game should be a draw on the last move."
    assert new_state.board[6] == 1, "Board should be updated."
    assert engine.is_game_over(new_state), "Game should be over."


def test_no_moves_after_game_over():
    """
    Test that moves are rejected after the game is over.
    """
    engine = Engine()
    # Create a winning state
    # X X X
    # O O .
    # . . .
    board = [0, 0, 0, 1, 1, -1, -1, -1, -1]
    state = State(board=board, turn=0, status=0)  # Player 0 won

    move = Move(player=0, position=5)

    # Move should be invalid because game is over
    assert not engine.validate_move(state, move), "Move should be invalid after game is over."

    # Attempting to apply should raise an error
    try:
        engine.apply_move(state, move)
        assert False, "apply_move should have raised ValueError"
    except ValueError as e:
        assert "Invalid move" in str(e), "Error message should indicate invalid move"


def test_agent_identifies_player():
    """
    Test that an agent can correctly identify which player it is from the initial game state.
    The agent receives a game state and must determine if it's player 0 or player 1.
    This simulates the initialization process where the agent determines its player ID
    from the 'turn' field of the initial state.
    """
    # Test for Player 0
    agent_0 = Agent(run_init=False)
    init_state_0 = State.initial({"turn": 0})  # Player 0's turn

    # Simulate the _read_init logic: agent determines player_id from init state's turn
    player_id_0 = init_state_0.turn
    agent_0.initialize({"player_id": player_id_0})

    assert agent_0.player_id == 0, "Agent should identify as player 0 when turn=0 in initial state"

    # Test for Player 1
    agent_1 = Agent(run_init=False)
    init_state_1 = State.initial({"turn": 1})  # Player 1's turn

    # Simulate the _read_init logic: agent determines player_id from init state's turn
    player_id_1 = init_state_1.turn
    agent_1.initialize({"player_id": player_id_1})

    assert agent_1.player_id == 1, "Agent should identify as player 1 when turn=1 in initial state"

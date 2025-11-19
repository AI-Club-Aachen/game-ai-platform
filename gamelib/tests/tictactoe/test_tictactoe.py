"""
Test suite for full game scenarios in gamelib.
"""

from gamelib.tictactoe.engine import Engine
from gamelib.tictactoe.gamestate import GameState as State
from gamelib.tictactoe.move import Move
from gamelib.tictactoe.examples.simple_agent import TicTacToeAgent as Agent


def test_validate_move():
    """
    Test the validate_move method of the TicTacToe engine.
    """
    engine = Engine()
    state = State.initial()
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

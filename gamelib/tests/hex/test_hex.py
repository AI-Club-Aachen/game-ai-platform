"""
Test suite for Hex GameState and Move validation/serialization.
"""

import pytest
from pydantic import ValidationError

from gamelib.hex.gamestate import GameState
from gamelib.hex.move import Move
from gamelib.hex.engine import Engine
from gamelib.hex.examples.simple_agent import HexAgent as Agent


def test_hex_initial_state():
    """Test standard Hex initial state default (11x11)."""
    state = GameState.initial()
    assert state.board_size == 11
    assert len(state.board) == 11
    assert all(len(row) == 11 for row in state.board)
    assert all(cell == -1 for row in state.board for cell in row)
    assert state.turn == 0
    assert state.status == -1

def test_hex_custom_size_initial_state():
    """Test creating Hex state with custom board size."""
    state = GameState.initial({"board_size": 5})
    assert state.board_size == 5
    assert len(state.board) == 5
    assert all(len(row) == 5 for row in state.board)
    assert all(cell == -1 for row in state.board for cell in row)
    assert state.turn == 0
    assert state.status == -1

def test_hex_gamestate_validation():
    """Test validation errors for invalid gamestates."""
    # invalid board length
    with pytest.raises(ValidationError):
        GameState(board_size=3, board=[[-1]*3]*2, turn=0, status=-1)
        
    # invalid cell value
    with pytest.raises(ValidationError):
        board = [[-1]*3 for _ in range(3)]
        board[0][0] = 5
        GameState(board_size=3, board=board, turn=0, status=-1)
        
    # invalid turn value
    with pytest.raises(ValidationError):
        GameState(board_size=3, board=[[-1]*3 for _ in range(3)], turn=2, status=-1)
        
    # invalid status
    with pytest.raises(ValidationError):
        GameState(board_size=3, board=[[-1]*3 for _ in range(3)], turn=0, status=5)

def test_hex_move_validation():
    """Test hex move constraints."""
    move = Move(player=0, position=[1, 2])
    assert move.player == 0
    assert move.position == [1, 2]

    with pytest.raises(ValidationError):
        Move(player=2, position=[0, 0])
        
    with pytest.raises(ValidationError):
        Move(player=0, position=[-1, 0])

def test_hex_serialization():
    """Test serialization and deserialization of hex gamestate and moves."""
    state = GameState.initial({"board_size": 7, "turn": 1, "status": -1})
    state.board[0][0] = 0
    state.board[1][1] = 1
    
    cloned_state = state.clone()
    assert cloned_state.board == state.board, "Cloned state board should match original."
    assert cloned_state.board_size == state.board_size
    assert cloned_state.turn == state.turn
    
    move = Move(player=1, position=[3, 4])
    
    state_json = state.to_json()
    cloned_state_json = cloned_state.to_json()
    assert state_json == cloned_state_json
    
    move_json = move.to_json()
    
    restored_state = GameState.from_json(state_json)
    restored_move = Move.from_json(move_json)
    
    assert restored_state.board == state.board
    assert restored_state.board_size == state.board_size
    assert restored_state.turn == state.turn
    
    assert restored_move.player == move.player
    assert restored_move.position == move.position

def test_full_game():
    """
    Test a full game of Hex.
    Note: This requires Hex Engine and Agent to be implemented.
    """
        
    agent1 = Agent()
    agent1.player_id = 0
    agent2 = Agent()
    agent2.player_id = 1
    engine = Engine()
    
    # Use a smaller board for tests to finish quicker
    state = GameState.initial({"board_size": 3})
    assert state.turn == 0, "Initial turn should be player 0."
    assert state.status == -1, "Initial game status should be ongoing (-1)."

    max_moves = 3 * 3
    moves = 0
    while not engine.is_game_over(state) and moves < max_moves:
        assert state.status == -1, "Game should be ongoing."
        if state.turn == 0:
            move = agent1.get_move(state)
        else:
            move = agent2.get_move(state)

        assert engine.validate_move(state, move), f"Move {move} should be valid."
        state = engine.apply_move(state, move)
        moves += 1

    assert state.status != -1, "Game should be over."
    assert state.status in [0, 1], "One of the players should win."


"""
Hex game engine implementation.
"""

from enum import Enum
from typing import override

from gamelib.engine_base import EngineBase
from gamelib.hex.gamestate import GameState as State
from gamelib.hex.move import Move


class GameStatus(Enum):
    ONGOING = -1
    DRAW = -2
    PLAYER_0_WINS = 0
    PLAYER_1_WINS = 1


class Engine(EngineBase):
    """
    Hex game engine implementation.
    """

    @override
    def __init__(self) -> None:
        """
        Initialize the game engine.
        """

    @override
    def validate_move(self, game_state: State, move: Move) -> bool:
        """
        Validate a move against the current game state.
        A move is valid if the game has not ended, the cell is empty, and it is the player's turn.
        """
        if not isinstance(game_state, State):
            raise TypeError("Invalid game state type.")
        if not isinstance(move, Move):
            raise TypeError("Invalid move type.")
        if game_state.status != GameStatus.ONGOING.value:
            return False  # Game is already over
        if move.player != game_state.turn:
            return False  # Not the player's turn
            
        if move.position[0] >= game_state.board_size or move.position[1] >= game_state.board_size:
            return False  # Position out of bounds
        if game_state.board[move.position[0]][move.position[1]] != -1:
            return False  # Cell is not empty
        return True

    @override
    def apply_move(self, game_state: State, move: Move) -> State:
        """
        Apply a move to the game state and return the new game state.
        """
        if not self.validate_move(game_state, move):
            raise ValueError("Invalid move")

        new_state = game_state.clone()
        
        new_state.board[move.position[0]][move.position[1]] = move.player
            
        new_state.turn = 1 - move.player  # Switch players
        new_state.status = self.get_status(new_state)  # Update status

        return new_state

    @override
    def get_status(self, game_state: State) -> int:
        """
        Get the winner of the game using BFS to find a connecting path.
        Player 0 connects Left to Right.
        Player 1 connects Top to Bottom.
        """
        board = game_state.board
        board_size = game_state.board_size

        def get_neighbors(r: int, c: int) -> list[tuple[int, int]]:
            # Hexagonal neighbors
            dirs = [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0)]
            neighbors = []
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < board_size and 0 <= nc < board_size:
                    neighbors.append((nr, nc))
            return neighbors
            
        def check_win(player: int) -> bool:
            visited = set()
            queue = []
            
            if player == 0:
                # Player 0: Left (col==0) to Right (col==board_size-1)
                for r in range(board_size):
                    if board[r][0] == player:
                        queue.append((r, 0))
                        visited.add((r, 0))
            else:
                # Player 1: Top (row==0) to Bottom (row==board_size-1)
                for c in range(board_size):
                    if board[0][c] == player:
                        queue.append((0, c))
                        visited.add((0, c))
            
            while queue:
                curr_r, curr_c = queue.pop(0)
                
                if player == 0 and curr_c == board_size - 1:
                    return True
                if player == 1 and curr_r == board_size - 1:
                    return True
                    
                for nxt_r, nxt_c in get_neighbors(curr_r, curr_c):
                    if (nxt_r, nxt_c) not in visited and board[nxt_r][nxt_c] == player:
                        visited.add((nxt_r, nxt_c))
                        queue.append((nxt_r, nxt_c))
            return False

        if check_win(0):
            return GameStatus.PLAYER_0_WINS.value
        if check_win(1):
            return GameStatus.PLAYER_1_WINS.value

        if all(cell != -1 for row in board for cell in row):
            return GameStatus.DRAW.value

        return GameStatus.ONGOING.value

    @override
    def is_game_over(self, game_state: State) -> bool:
        """
        Check if the game is over based on the current game state.
        """
        return game_state.status != GameStatus.ONGOING.value

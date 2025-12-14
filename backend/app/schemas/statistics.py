from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class Match(BaseModel):
    match_id: uuid
    player_a_id: uuid
    player_b_id: uuid
    winner_id: uuid | None # In case we have any ties
    created_at: datetime

class Player(BaseModel):
    player_id: uuid
    elo: float               # For now only winrate
    games_played: int        # 0 by default
    wins: int   
    losses: int

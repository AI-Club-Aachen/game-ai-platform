"""For now only calculate the winrate given wins and losses of a player."""

from app.schemas.statistics import Player

def calculate_winrate(player: Player) -> float:
    """
    For now, just calculate a simple winrate wins/total given a player
    """
    total = player.wins + player.losses
    if total == 0:
        player.elo = 0.0
        return player
    player.elo = round(player.wins / total, 4) #  4 decimals should suffice (hopefully)
    return player


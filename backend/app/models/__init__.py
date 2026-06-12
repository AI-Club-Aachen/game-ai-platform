"""
SQLModel database models
"""

from .agent import Agent
from .game import GameType
from .job import BuildJob, JobStatus, MatchJob
from .match import Match, MatchStatus
from .platform_flag import PlatformFlag
from .submission import Submission
from .tournament import (
    Tournament,
    TournamentEntrant,
    TournamentGame,
    TournamentMatchup,
    TournamentStatus,
)
from .user import User, UserRole


__all__ = [
    "User",
    "UserRole",
    "Submission",
    "Match",
    "MatchStatus",
    "GameType",
    "Agent",
    "BuildJob",
    "MatchJob",
    "JobStatus",
    "PlatformFlag",
    "Tournament",
    "TournamentEntrant",
    "TournamentGame",
    "TournamentMatchup",
    "TournamentStatus",
]

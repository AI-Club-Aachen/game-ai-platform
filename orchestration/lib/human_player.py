"""
A human seat in a match, played through the web UI. The backend pushes the
human's moves onto a Redis list; the runner BLPOPs it on the human's turn.
"""

import json
import logging
import os
import time
from collections.abc import Awaitable, Callable
from typing import Any

from redis import asyncio as aioredis

from lib.agent_communication import AgentCommunicationError, AgentTimeLimitError

logger = logging.getLogger(__name__)

HUMAN_PLAYER_ID = "human"  # the human's id in results (winner, scores)

# Keeps the match from being failed as stale (backend MATCH_STALE_TIMEOUT_SECONDS).
HEARTBEAT_INTERVAL_SECONDS = 15.0


def human_moves_key(match_id: str) -> str:
    """Must match backend/app/core/queue.py."""
    return f"match:{match_id}:human_moves"


class HumanResignedError(Exception):
    """The human player resigned."""


class HumanPlayer:
    """Stands in for ``AgentProcess`` in the match loop; moves arrive over Redis."""

    is_human = True
    container_id: str | None = None
    stderr_tail = ""

    def __init__(self, match_id: str, player_id: int, redis_url: str | None = None) -> None:
        self.match_id = match_id
        self.player_id = player_id
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379")
        self._redis: aioredis.Redis | None = None
        self._key = human_moves_key(match_id)

    def verify_image(self) -> None:
        pass

    async def start(self) -> None:
        try:
            self._redis = aioredis.from_url(self._redis_url, encoding="utf8", decode_responses=True)
            await self._redis.ping()
        except Exception as e:
            raise AgentCommunicationError(f"Player {self.player_id} (human): Redis unavailable: {e}") from e

    async def send_init(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def resume(self) -> None:
        pass

    async def cleanup(self) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.delete(self._key)
        except Exception as e:
            logger.debug("[%s] Failed to delete human input list: %s", self.match_id, e)
        try:
            await self._redis.aclose()
        except Exception:
            pass
        self._redis = None

    async def discard_pending(self) -> None:
        """Drop moves left over after the human's turn (double clicks), but keep a resignation."""
        if self._redis is None:
            return
        pending = await self._redis.lrange(self._key, 0, -1)
        if not pending:
            return
        await self._redis.delete(self._key)
        if any(_parse(raw).get("type") == "resign" for raw in pending):
            await self._redis.rpush(self._key, json.dumps({"type": "resign"}))

    async def get_input(
        self,
        timeout: float,
        heartbeat: Callable[[], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        """
        Return the next move. Raises ``HumanResignedError`` or, after ``timeout``
        seconds, ``AgentTimeLimitError``. Malformed messages are skipped.
        """
        if self._redis is None:
            raise RuntimeError("HumanPlayer.start() was not called")

        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            # BLPOP treats a 0 timeout as "block forever".
            if remaining <= 0.01:  # noqa: PLR2004
                raise AgentTimeLimitError(
                    f"Player {self.player_id} (human) did not move within {timeout:g}s"
                )
            wait = min(remaining, HEARTBEAT_INTERVAL_SECONDS)
            item = await self._redis.blpop(self._key, timeout=wait)
            if item is None:
                if heartbeat is not None:
                    await heartbeat()
                continue

            message = _parse(item[1])
            if message.get("type") == "resign":
                raise HumanResignedError(f"Player {self.player_id} (human) resigned")
            if message.get("type") == "move" and isinstance(message.get("move"), dict):
                return message["move"]
            logger.warning("[%s] Ignoring malformed human input: %r", self.match_id, item[1])


def _parse(raw: str) -> dict[str, Any]:
    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return message if isinstance(message, dict) else {}

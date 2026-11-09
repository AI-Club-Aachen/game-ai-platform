"""
A human seat in a match, played through the web UI.

The backend pushes the human's input onto a Redis list
(``POST /matches/{id}/human-move`` and ``/resign``); the match runner BLPOPs it
while it is the human's turn. ``HumanPlayer`` mirrors the parts of
``AgentProcess`` that the match loop uses, so it can sit in the same player list.
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

# Player id used for the human seat in results (``result["winner"]``, scores).
HUMAN_PLAYER_ID = "human"

# How often to ping the backend while waiting on the human, so the match is not
# marked stale (MATCH_STALE_TIMEOUT_SECONDS defaults to 60s).
HEARTBEAT_INTERVAL_SECONDS = 15.0


def human_moves_key(match_id: str) -> str:
    """Redis list holding the human's input. Must match backend/app/core/queue.py."""
    return f"match:{match_id}:human_moves"


class HumanResignedError(Exception):
    """The human player resigned."""


class HumanPlayer:
    """Human seat: no container; moves arrive over Redis."""

    is_human = True
    container_id: str | None = None
    stderr_tail = ""

    def __init__(self, match_id: str, player_id: int, redis_url: str | None = None) -> None:
        self.match_id = match_id
        self.player_id = player_id
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379")
        self._redis: aioredis.Redis | None = None
        self._key = human_moves_key(match_id)

    # --- AgentProcess-compatible no-ops ------------------------------------

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

    # --- Human input -------------------------------------------------------

    async def discard_pending(self) -> None:
        """
        Drop queued moves (e.g. a double-submitted move) once the human's turn is
        over. A queued resignation is kept so it still applies on the next turn.
        """
        if self._redis is None:
            return
        pending = await self._redis.lrange(self._key, 0, -1)
        if not pending:
            return
        await self._redis.delete(self._key)
        if any('"resign"' in raw for raw in pending):
            await self._redis.rpush(self._key, json.dumps({"type": "resign"}))

    async def get_input(
        self,
        timeout: float,
        heartbeat: Callable[[], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        """
        Wait for the next input message: ``{"type": "move", "move": {...}}``.

        Raises ``HumanResignedError`` on a resignation and ``AgentTimeLimitError``
        when ``timeout`` seconds pass without a move. Malformed messages are skipped.
        """
        if self._redis is None:
            raise RuntimeError("HumanPlayer.start() was not called")

        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            # Redis rounds BLPOP timeouts to milliseconds and treats 0 as "block
            # forever", so stop slightly early instead of passing a ~0 timeout.
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

            _, raw = item
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("[%s] Ignoring malformed human input: %r", self.match_id, raw)
                continue
            if not isinstance(message, dict):
                continue
            if message.get("type") == "resign":
                raise HumanResignedError(f"Player {self.player_id} (human) resigned")
            if message.get("type") == "move" and isinstance(message.get("move"), dict):
                return message["move"]
            logger.warning("[%s] Ignoring unknown human input: %r", self.match_id, message)

"""
Redis pub/sub manager for real-time match game state events.

Allows the SSE endpoint to subscribe to live game state updates
published by the match service whenever a match's game_state is updated.
"""

import json
import logging
from typing import Any

from redis import asyncio as aioredis

from app.core.config import settings


logger = logging.getLogger(__name__)


def _channel_name(match_id: str) -> str:
    """Return the Redis pub/sub channel name for a given match."""
    return f"match:{match_id}:state"


class MatchEventPublisher:
    """Publishes match game state updates to Redis pub/sub."""

    def __init__(self, redis_url: str = settings.REDIS_URL) -> None:
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None

    async def _ensure_connected(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url, encoding="utf8", decode_responses=True
            )
        return self._redis

    async def publish_game_state(
        self,
        match_id: str,
        game_state: dict[str, Any],
        status: str,
        logs: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Publish a game state update event for a match."""
        redis = await self._ensure_connected()
        channel = _channel_name(match_id)
        payload = json.dumps({
            "game_state": game_state,
            "status": status,
            "logs": logs,
            "result": result,
        })
        await redis.publish(channel, payload)
        logger.debug("Published game state update to %s", channel)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


async def subscribe_match_events(
    match_id: str,
    redis_url: str = settings.REDIS_URL,
) -> "aioredis.client.PubSub":
    """
    Create a Redis pub/sub subscription for a match's game state events.

    Returns a PubSub object. Caller is responsible for calling .unsubscribe()
    and .aclose() when done.
    """
    redis = aioredis.from_url(redis_url, encoding="utf8", decode_responses=True)
    pubsub = redis.pubsub()
    channel = _channel_name(match_id)
    await pubsub.subscribe(channel)
    logger.debug("Subscribed to %s", channel)
    return pubsub


# Singleton publisher for use by the match service
match_event_publisher = MatchEventPublisher()

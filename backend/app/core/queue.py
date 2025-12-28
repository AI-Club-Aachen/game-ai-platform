import json
import logging
from typing import Any
from uuid import UUID

from redis import asyncio as aioredis


logger = logging.getLogger(__name__)


class JobQueue:
    """
    Manages enqueuing jobs to Redis for worker processes.
    """

    def __init__(self, redis_url: str = "redis://redis:6379") -> None:
        self.redis_url = redis_url
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        if not self._redis:
            self._redis = aioredis.from_url(self.redis_url, encoding="utf8", decode_responses=True)
            logger.info("JobQueue connected to Redis")

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def _enqueue(self, queue_name: str, payload: dict[str, Any]) -> None:
        if not self._redis:
            await self.connect()

        # Ensure redis is connected
        if self._redis:
            await self._redis.rpush(queue_name, json.dumps(payload))
            logger.info(f"Enqueued job to {queue_name}: {payload}")
        else:
            logger.error(f"Failed to enqueue job to {queue_name}, Redis not connected")

    async def enqueue_build(self, submission_id: UUID, zip_path: str) -> None:
        """Enqueue a build job for a submission."""
        payload = {
            "type": "build",
            "submission_id": str(submission_id),
            "zip_path": zip_path,
        }
        await self._enqueue("queue:builds", payload)

    async def enqueue_match(self, match_id: UUID, config: dict[str, Any]) -> None:
        """Enqueue a match execution job."""
        payload = {
            "type": "match",
            "match_id": str(match_id),
            "config": config,
        }
        await self._enqueue("queue:matches", payload)


# Singleton instance
job_queue = JobQueue()

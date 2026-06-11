import json
import logging
from typing import Any
from uuid import UUID

from redis import asyncio as aioredis

from app.core.config import settings


logger = logging.getLogger(__name__)


class JobQueue:
    """
    Manages enqueuing jobs to Redis for worker processes.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        # Default to configured REDIS_URL (carries password and db index).
        self.redis_url = redis_url if redis_url is not None else settings.REDIS_URL
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        if not self._redis:
            self._redis = aioredis.from_url(self.redis_url, encoding="utf8", decode_responses=True)
            logger.info("JobQueue connected to Redis")

    async def close(self) -> None:
        if self._redis:
            await getattr(self._redis, "aclose", self._redis.close)()
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

    async def enqueue_build(
        self,
        submission_id: UUID,
        job_id: UUID,
        cleanup_image: bool = False
    ) -> None:
        """Enqueue a build job for a submission."""
        payload = {
            "type": "build",
            "submission_id": str(submission_id),
            "job_id": str(job_id),
            "cleanup_image": cleanup_image,
        }
        await self._enqueue("queue:builds", payload)

    async def enqueue_match(self,
        match_id: UUID,
        config: dict[str, Any],
        job_id: UUID,
        agent_ids: list[UUID],
        create_images: bool
    ) -> None:
        """Enqueue a match execution job."""
        payload = {
            "type": "match",
            "match_id": str(match_id),
            "job_id": str(job_id),
            "config": config,
            "agent_ids": [str(aid) for aid in agent_ids],
            "create_images": create_images,
        }
        await self._enqueue("queue:matches", payload)


# Singleton instance
job_queue = JobQueue(redis_url=settings.REDIS_URL)

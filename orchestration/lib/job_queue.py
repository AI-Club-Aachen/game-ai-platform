"""
Tools for using Redis task queue
Redis URL is in REDIS_URL environment variable.
"""

import json
import logging
import os
from typing import Any

from redis import asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisQueueError(Exception):
    """Base exception for Redis queue operations."""


class JobQueue:
    """
    Abstraction layer for accessing the backend's Redis job queues.

    This class handles connection management and job retrieval from Redis queues,
    allowing workers to focus on job processing logic.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        """
        Initialize Redis queue client.

        Args:
            redis_url: Redis connection URL. If None, uses REDIS_URL environment variable
                      or defaults to "redis://redis:6379"
        """
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379")

        self.redis_url = redis_url
        self._redis: aioredis.Redis | None = None
        self._is_connected = False

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if self._is_connected:
            return

        try:
            self._redis = aioredis.from_url(
                self.redis_url, encoding="utf8", decode_responses=True
            )
            # Verify connection
            await self._redis.ping()
            self._is_connected = True
            logger.info(f"Connected to Redis: {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise RedisQueueError(f"Redis connection failed: {e}") from e

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._is_connected = False
            logger.info("Redis connection closed")

    async def _ensure_connected(self) -> None:
        """Ensure Redis is connected, connecting if necessary."""
        if not self._is_connected:
            await self.connect()

    async def pop_job(
        self, queue_name: str, timeout: int = 0
    ) -> dict[str, Any] | None:
        """
        Pop a job from the specified queue.

        Uses blocking pop (BLPOP) to wait for jobs.

        Args:
            queue_name: Name of the queue (e.g., "queue:builds", "queue:matches")
            timeout: Block timeout in seconds. 0 means block indefinitely.

        Returns:
            Parsed job dictionary, or None if timeout reached

        Raises:
            RedisQueueError: If Redis operation fails
        """
        await self._ensure_connected()

        try:
            result = await self._redis.blpop(queue_name, timeout=timeout)
            if result is None:
                return None

            # BLPOP returns (key, value) tuple
            _, job_str = result
            job = json.loads(job_str)
            logger.debug(f"Popped job from {queue_name}: {job}")
            return job

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse job JSON from {queue_name}: {e}")
            raise RedisQueueError(f"Invalid job JSON: {e}") from e
        except Exception as e:
            logger.error(f"Error popping job from {queue_name}: {e}")
            raise RedisQueueError(f"Queue operation failed: {e}") from e

    async def pop_build_job(self, timeout: int = 0) -> dict[str, Any] | None:
        """
        Pop a build job from the builds queue.

        Expected job format:
        {
            "type": "build",
            "submission_id": "<uuid>",
            "zip_path": "<path>"
        }

        Args:
            timeout: Block timeout in seconds. 0 means block indefinitely.

        Returns:
            Job dictionary or None if timeout reached
        """
        return await self.pop_job("queue:builds", timeout=timeout)

    async def pop_match_job(self, timeout: int = 0) -> dict[str, Any] | None:
        """
        Pop a match job from the matches queue.

        Expected job format:
        {
            "type": "match",
            "match_id": "<uuid>",
            "config": {<match configuration>}
        }

        Args:
            timeout: Block timeout in seconds. 0 means block indefinitely.

        Returns:
            Job dictionary or None if timeout reached
        """
        return await self.pop_job("queue:matches", timeout=timeout)

    async def get_queue_length(self, queue_name: str) -> int:
        """
        Get the number of jobs in a queue.

        Args:
            queue_name: Name of the queue

        Returns:
            Number of jobs in the queue
        """
        await self._ensure_connected()

        try:
            length = await self._redis.llen(queue_name)
            return length
        except Exception as e:
            logger.error(f"Error getting length of {queue_name}: {e}")
            raise RedisQueueError(f"Failed to get queue length: {e}") from e


def get_redis_queue(redis_url: str | None = None) -> JobQueue:
    """
    Factory function to create a JobQueue instance.

    Args:
        redis_url: Optional Redis URL. If None, uses REDIS_URL env var.

    Returns:
        JobQueue instance
    """
    return JobQueue(redis_url=redis_url)

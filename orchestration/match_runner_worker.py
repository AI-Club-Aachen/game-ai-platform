# ruff: noqa: E402
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Ensure backend modules are importable
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from redis import asyncio as aioredis
from sqlmodel import Session, create_engine

try:
    from app.core.config import settings
    from app.models.match import Match, MatchStatus
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("match_runner_worker")

DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)
engine = create_engine(DATABASE_URL)


async def run_match_simulation(config: dict) -> dict:
    """
    Placeholder for actual match execution logic.
    For now, it sleeps and returns a dummy result.
    In the future, this will use docker-py to spin up agent containers and a game engine.
    """
    await asyncio.sleep(2)  # Simulate work

    # Mock result
    return {
        "winner": "agent_1" if hash(str(config)) % 2 == 0 else "agent_2",
        "scores": {"agent_1": 10, "agent_2": 5},
        "reason": "Turn limit reached",
    }


async def process_match(match_id: str, config: dict):
    logger.info(f"Processing match {match_id}")

    with Session(engine) as session:
        match_obj = session.get(Match, match_id)
        if not match_obj:
            logger.error(f"Match {match_id} not found in DB")
            return

        match_obj.status = MatchStatus.RUNNING
        session.add(match_obj)
        session.commit()

        try:
            logger.info("Starting Match execution...")
            result = await run_match_simulation(config)

            logger.info("Match finished.")
            match_obj.status = MatchStatus.COMPLETED
            match_obj.result = result
            match_obj.logs = "Match completed successfully."
            session.add(match_obj)
            session.commit()

        except Exception as e:
            logger.exception(f"Match execution failed for {match_id}")
            match_obj.status = MatchStatus.FAILED
            match_obj.logs = str(e)
            session.add(match_obj)
            session.commit()


async def worker_loop():
    redis_url = "redis://redis:6379"
    if os.getenv("ENVIRONMENT") == "development" and "redis" not in os.getenv("REDIS_HOST", ""):
        redis_url = "redis://localhost:6379"

    logger.info(f"Connecting to Redis at {redis_url}")
    redis = aioredis.from_url(redis_url, encoding="utf8", decode_responses=True)

    logger.info("Match Runner Worker started. Waiting for jobs...")

    while True:
        try:
            _, data_str = await redis.blpop("queue:matches", timeout=0)

            job_data = json.loads(data_str)
            logger.info(f"Received job: {job_data}")

            if job_data.get("type") == "match":
                await process_match(job_data["match_id"], job_data["config"])
            else:
                logger.warning(f"Unknown job type: {job_data.get('type')}")

        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("Worker stopped")

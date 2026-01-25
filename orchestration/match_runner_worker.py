# ruff: noqa: E402
import asyncio
import logging

from lib.backend_api import BackendAPI
from lib.job_queue import JobQueue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("match_runner_worker")


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


async def process_match(match_id: str, config: dict, api: BackendAPI):
    logger.info(f"Processing match {match_id}")

    try:
        # Update status to RUNNING
        await api.update_match(match_id, status="running")

        logger.info("Starting Match execution...")
        result = await run_match_simulation(config)

        logger.info("Match finished.")
        # Update status to COMPLETED with result
        await api.update_match(
            match_id,
            status="completed",
            result=result,
            logs="Match completed successfully.",
        )

    except Exception as e:
        logger.exception(f"Match execution failed for {match_id}")
        await api.update_match(
            match_id,
            status="failed",
            logs=str(e),
        )


async def worker_loop():
    queue = JobQueue()
    api = BackendAPI()

    await queue.connect()

    logger.info("Match Runner Worker started. Waiting for jobs...")

    try:
        while True:
            try:
                job_data = await queue.pop_match_job(timeout=0)
                if job_data is None:
                    continue

                logger.info(f"Received job: {job_data}")

                if job_data.get("type") == "match":
                    await process_match(job_data["match_id"], job_data["config"], api)
                else:
                    logger.warning(f"Unknown job type: {job_data.get('type')}")

            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(1)
    finally:
        await queue.close()
        await api.close()


if __name__ == "__main__":
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("Worker stopped")

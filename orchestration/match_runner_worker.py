# ruff: noqa: E402
import asyncio
import logging
import os
import sys

if os.getenv("USE_LOCAL_GAMELIB", "false").lower() == "true":
    sys.path.insert(0, "/gamelib")

import docker

from lib.backend_api import BackendAPI
from lib.job_queue import JobQueue
from lib.match_manager import _get_agent_image_tags, run_match
from lib.agent_builder import build_images_for_agents

_log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("match_runner_worker")
logger.info(f"Log level set to {_log_level_name}")


async def process_match(match_id: str, config: dict, agent_ids: list[str], api: BackendAPI, create_images: bool):
    logger.info(f"Processing match {match_id}")

    image_tags = []

    try:
        if create_images:
            logger.info(f"Creating images for agents: {agent_ids}")
            image_tags = await build_images_for_agents(agent_ids, api)
        else:
            logger.debug(f"[{match_id}] Resolving image tags for {len(agent_ids)} agent(s): {agent_ids}")
            image_tags = await _get_agent_image_tags(agent_ids, api)
        logger.debug(f"[{match_id}] Image tags for {agent_ids}: {image_tags}")

        # Update status to RUNNING
        await api.update_match(match_id, status="running")

        logger.info("Starting Match execution...")
        result = await run_match(match_id, config, agent_ids, image_tags, api)

        if result.get("status") == "error":
            logger.error(f"Match execution returned error: {result.get('reason')}")
            await api.update_match(
                match_id,
                status="failed",
                result=result,
            )
            return

        logger.info("Match finished.")
        status = "completed"
        valid_reasons = ["Game finished", "Draw", "Turn limit reached", "Time limit exceeded"]
        if result.get("reason") not in valid_reasons:
            status = "client_error"

        # Update status to COMPLETED or CLIENT_ERROR with result
        await api.update_match(
            match_id,
            status=status,
            result=result,
        )

    except Exception as e:
        logger.exception(f"Match execution failed for {match_id}")
        logger.error(f"Error details: {e}")
        await api.update_match(
            match_id,
            status="failed",
        )
    finally:
        logger.info(f"Cleaning up Docker images for match {match_id}...")
        client = docker.from_env()
        for image_tag in image_tags:
            logger.info(f"Cleaning up image: {image_tag}")
            try:
                client.images.remove(image_tag, force=True)
            except Exception as e:
                logger.error(f"Failed to clean up image {image_tag}: {e}")


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
                    await process_match(
                        job_data["match_id"],
                        job_data["config"],
                        job_data.get("agent_ids", []),
                        api,
                        job_data["create_images"],
                    )
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

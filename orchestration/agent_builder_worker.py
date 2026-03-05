# ruff: noqa: E402
import asyncio
import logging
from pathlib import Path

from lib.agent_builder import build_from_zip
from lib.backend_api import BackendAPI
from lib.job_queue import JobQueue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_builder_worker")


async def process_build(submission_id: str, job_id: str, zip_path: str, api: BackendAPI):
    logger.info(f"Processing build for job {job_id} (submission {submission_id})")

    try:
        # Update status to RUNNING
        await api.update_build_job(job_id, status="running", logs="Starting build...\n")

        zip_p = Path(zip_path)
        if not zip_p.exists():
            raise FileNotFoundError(f"Zip file not found: {zip_path}")

        zip_bytes = zip_p.read_bytes()

        logger.info("Starting Docker build...")
        result = await asyncio.to_thread(
            build_from_zip, zip_bytes=zip_bytes, owner_id=submission_id
        )

        logger.info(f"Build success! Image ID: {result['image_id']}")

        # Update status to COMPLETED with image details
        await api.update_build_job(
            job_id,
            status="completed",
            logs="Build success!\n",
            image_id=result["image_id"],
            image_tag=result["tag"],
        )

    except Exception as e:
        logger.exception(f"Build failed for job {job_id}: {e}")
        await api.update_build_job(
            job_id,
            status="failed",
            logs=f"Build failed: {e}\n",
        )


async def worker_loop():
    queue = JobQueue()
    api = BackendAPI()

    await queue.connect()

    logger.info("Agent Builder Worker started. Waiting for jobs...")

    try:
        while True:
            try:
                job_data = await queue.pop_build_job(timeout=0)
                if job_data is None:
                    continue

                logger.info(f"Received job: {job_data}")

                if job_data.get("type") == "build":
                    await process_build(job_data["submission_id"], job_data["job_id"], job_data["zip_path"], api)
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

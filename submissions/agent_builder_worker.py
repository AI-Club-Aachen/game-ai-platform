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

import docker
from redis import asyncio as aioredis
from sqlmodel import Session, create_engine

try:
    from app.core.config import settings
    from app.models.submission import Submission, SubmissionStatus
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    sys.exit(1)

try:
    from agent_builder import build_from_zip
except ImportError:
    from submissions.agent_builder import build_from_zip

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_builder_worker")

DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)
engine = create_engine(DATABASE_URL)


async def process_build(submission_id: str, zip_path: str):
    logger.info(f"Processing build for submission {submission_id}")
    
    with Session(engine) as session:
        submission = session.get(Submission, submission_id)
        if not submission:
            logger.error(f"Submission {submission_id} not found in DB")
            return

        submission.status = SubmissionStatus.BUILDING
        session.add(submission)
        session.commit()

        try:
            zip_p = Path(zip_path)
            if not zip_p.exists():
                raise FileNotFoundError(f"Zip file not found: {zip_path}")
            
            zip_bytes = zip_p.read_bytes()

            logger.info("Starting Docker build...")
            result = await asyncio.to_thread(
                build_from_zip, 
                zip_bytes=zip_bytes, 
                owner_id=str(submission.user_id)
            )
            
            logger.info(f"Build success! Image ID: {result['image_id']}")

            submission.status = SubmissionStatus.COMPLETED
            submission.image_id = result["image_id"]
            submission.image_tag = result["tag"]
            submission.logs = "Build successful" 
            session.add(submission)
            session.commit()

        except Exception as e:
            logger.exception(f"Build failed for submission {submission_id}")
            submission.status = SubmissionStatus.FAILED
            submission.logs = str(e)
            session.add(submission)
            session.commit()


async def worker_loop():
    redis_url = "redis://redis:6379"
    if os.getenv("ENVIRONMENT") == "development" and "redis" not in os.getenv("REDIS_HOST", ""):
         redis_url = "redis://localhost:6379"

    logger.info(f"Connecting to Redis at {redis_url}")
    redis = aioredis.from_url(redis_url, encoding="utf8", decode_responses=True)

    logger.info("Agent Builder Worker started. Waiting for jobs...")
    
    while True:
        try:
            _, data_str = await redis.blpop("queue:builds", timeout=0)
            
            job_data = json.loads(data_str)
            logger.info(f"Received job: {job_data}")
            
            if job_data.get("type") == "build":
                await process_build(job_data["submission_id"], job_data["zip_path"])
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

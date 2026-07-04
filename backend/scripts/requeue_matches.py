import asyncio
import sys
from pathlib import Path
from uuid import UUID


# Ensure the parent directory is in sys.path so we can import app
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Session, select

from app.core.queue import job_queue
from app.db.connection import engine
from app.models.job import JobStatus, MatchJob
from app.models.match import Match, MatchStatus


async def main() -> None:
    print("Connecting to database...")
    with Session(engine) as session:
        # Get all queued matches
        statement = select(Match).where(Match.status == MatchStatus.QUEUED)
        queued_matches = list(session.exec(statement).all())

        if not queued_matches:
            print("No queued matches found in the database.")
            return

        print(f"Found {len(queued_matches)} queued matches in the database. Re-queueing them in Redis...")

        await job_queue.connect()

        requeued_count = 0
        for match in queued_matches:
            # Find the corresponding queued match job
            job_stmt = select(MatchJob).where(
                MatchJob.match_id == match.id,
                MatchJob.status == JobStatus.QUEUED
            )
            job = session.exec(job_stmt).first()
            if not job:
                print(f"Warning: No queued MatchJob found for Match {match.id}. Creating a new one...")
                job = MatchJob(match_id=match.id, status=JobStatus.QUEUED, sa_column_kwargs={"create_images": True})
                # Fallback mapping
                job = MatchJob(match_id=match.id, status=JobStatus.QUEUED, create_images=True)
                session.add(job)
                session.commit()
                session.refresh(job)

            # Safely convert agent IDs to UUID objects
            agent_uuids = [UUID(str(aid)) for aid in match.agent_ids]

            print(f"Enqueuing Match {match.id} (Job: {job.id})")
            await job_queue.enqueue_match(
                match_id=match.id,
                config=match.config,
                job_id=job.id,
                agent_ids=agent_uuids,
                create_images=job.create_images
            )
            requeued_count += 1

        print(f"Successfully re-queued {requeued_count} matches in Redis.")
        await job_queue.close()

if __name__ == "__main__":
    asyncio.run(main())

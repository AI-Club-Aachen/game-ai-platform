import os
import sys
import uuid
from pathlib import Path


# Add the parent directory to sys.path so we can import the app module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.connection import engine
from app.models.agent import Agent
from app.models.game import GameType
from app.models.job import BuildJob, JobStatus
from app.models.submission import Submission
from app.models.user import User, UserRole


def _get_or_create_seed_user(session: Session) -> User:
    """Gets the seed user or creates it if it doesn't exist."""
    user = session.exec(select(User).where(User.email == "seeduser@example.com")).first()
    if not user:
        # Create a valid password that passes security checks
        plain_pass = "TestP@ssw0rd!"  # noqa: S105
        real_hash = hash_password(plain_pass)

        user = User(
            username="seeduser",
            email="seeduser@example.com",
            password_hash=real_hash,
            role=UserRole.ADMIN,
            email_verified=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"Created test user: {user.username} with email: {user.email} and password: {plain_pass}")
    else:
        print(f"Test user already exists: {user.username}")
    return user


def _create_build_logs(status: JobStatus, sub_id: int) -> str:
    """Generates dummy logs based on the job status."""
    if status == JobStatus.QUEUED:
        return ""

    logs = f"Starting build for submission {sub_id}\nResolving dependencies...\nBuilding image...\n"
    if status == JobStatus.COMPLETED:
        logs += "Build successful!\n"
    elif status == JobStatus.FAILED:
        logs += "Error: Failed to build image step 3.\n"
    return logs


def _create_submissions_and_jobs(session: Session, user: User) -> uuid.UUID | None:
    """Creates test submissions and jobs. Returns the ID of a completed submission if any."""
    existing_submissions = session.exec(select(Submission).where(Submission.user_id == user.id)).all()
    if existing_submissions:
        print("Submissions already exist for seeduser. Skipping creation.")
        # Try to find an existing completed submission to return
        completed = session.exec(
            select(Submission)
            .join(BuildJob)
            .where(Submission.user_id == user.id)
            .where(BuildJob.status == JobStatus.COMPLETED)
        ).first()
        return completed.id if completed else None

    active_sub_id = None
    completed_sub_id = uuid.uuid4()  # Pre-allocate one id for the completed submission

    statuses = [JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.COMPLETED, JobStatus.FAILED]

    active_sub_id = None

    for i, status in enumerate(statuses):
        sub_id = completed_sub_id if status == JobStatus.COMPLETED else uuid.uuid4()
        sub = Submission(
            id=sub_id,
            user_id=user.id,
            name=f"seed-submission-{i + 1}",
            game_type=GameType.CHESS,
            object_path=f"seeded/submissions/agent_v{i}.zip",
        )
        session.add(sub)
        session.commit()
        session.refresh(sub)
        print(f"Created submission {sub.id}")

        if status == JobStatus.COMPLETED:
            active_sub_id = sub.id

        job = BuildJob(
            submission_id=sub.id,
            status=status,
            logs=_create_build_logs(status, sub.id),
            image_id=f"seeded-image-{sub.id}" if status == JobStatus.COMPLETED else None,
            image_tag="latest" if status == JobStatus.COMPLETED else None,
        )
        session.add(job)
        session.commit()
        print(f"Created build job for submission {sub.id} with status {status}")

    return active_sub_id


def _get_or_create_seed_agent(session: Session, user: User) -> Agent:
    """Creates a seed agent without an active submission for the user if they don't have one."""
    agent = session.exec(select(Agent).where(Agent.user_id == user.id)).first()
    if not agent:
        agent = Agent(
            id=uuid.uuid4(),
            user_id=user.id,
            name="seed-agent",
            game_type=GameType.CHESS,
            active_submission_id=None,
            stats={"rating": 1500, "matches_played": 0},
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        print(f"Created Agent {agent.id}")
    return agent


def seed() -> None:
    """Main seed function."""
    if settings.is_production:
        print("Cannot run seed script in production environment.")
        return

    # Using settings for SEED_DB check if it's there, or fallback to env
    if os.getenv("SEED_DB") != "true":
        print("SEED_DB environment variable is not 'true'. Skipping seed.")
        return

    print("Seeding database with test data...")

    with Session(engine) as session:
        user = _get_or_create_seed_user(session)
        agent = _get_or_create_seed_agent(session, user)

        # Try to create submissions
        active_sub_id = _create_submissions_and_jobs(session, user)

        if active_sub_id and agent.active_submission_id is None:
            agent.active_submission_id = active_sub_id
            session.add(agent)
            session.commit()

        print("Database seeding complete.")


if __name__ == "__main__":
    seed()

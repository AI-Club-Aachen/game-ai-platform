import os
import sys

# Add the parent directory to sys.path so we can import the app module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import Session, select
from app.db.connection import engine
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.agent import Agent
from app.models.submission import Submission
from app.models.job import BuildJob, JobStatus


def seed():
    if settings.is_production:
        print("Cannot run seed script in production environment.")
        return

    if os.getenv("SEED_DB") != "true":
        print("SEED_DB environment variable is not 'true'. Skipping seed.")
        return

    print("Seeding database with test data...")

    with Session(engine) as session:
        # Check if test user exists
        user = session.exec(select(User).where(User.email == "seeduser@example.com")).first()
        if not user:
            from app.core.security import hash_password
            
            # Create a valid password that passes security checks
            plain_pass = "TestP@ssw0rd!"
            real_hash = hash_password(plain_pass)
            
            user = User(
                username="seeduser",
                email="seeduser@example.com",
                password_hash=real_hash,
                role=UserRole.USER,
                email_verified=True,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"Created test user: {user.username} with email: {user.email} and password: {plain_pass}")
        else:
            print(f"Test user already exists: {user.username}")

        # Ensure we don't infinitely insert if the script is run multiple times
        existing_submissions = session.exec(select(Submission).where(Submission.user_id == user.id)).all()
        if existing_submissions:
            print("Submissions already exist for seeduser. Skipping creation.")
            return

        # Create multiple submissions with different job statuses
        statuses = [
            JobStatus.QUEUED,
            JobStatus.RUNNING,
            JobStatus.COMPLETED,
            JobStatus.FAILED
        ]

        active_sub_id = None

        for i, status in enumerate(statuses):
            # Create submission
            sub = Submission(
                user_id=user.id,
                object_path=f"seeded/submissions/agent_v{i}.zip"
            )
            session.add(sub)
            session.commit()
            session.refresh(sub)
            print(f"Created submission {sub.id}")

            if status == JobStatus.COMPLETED:
                active_sub_id = sub.id

            # Create build job for the submission
            logs_content = f"Starting build for submission {sub.id}\n"
            if status != JobStatus.QUEUED:
                logs_content += "Resolving dependencies...\nBuilding image...\n"
                if status == JobStatus.COMPLETED:
                    logs_content += "Build successful!\n"
                elif status == JobStatus.FAILED:
                    logs_content += "Error: Failed to build image step 3.\n"
            else:
                logs_content = ""

            job = BuildJob(
                submission_id=sub.id,
                status=status,
                logs=logs_content,
                image_id=f"seeded-image-{sub.id}" if status == JobStatus.COMPLETED else None,
                image_tag="latest" if status == JobStatus.COMPLETED else None
            )
            session.add(job)
            session.commit()
            print(f"Created build job for submission {sub.id} with status {status}")

        # Create an Agent if we have a completed submission
        if active_sub_id:
            agent = session.exec(select(Agent).where(Agent.user_id == user.id)).first()
            if not agent:
                agent = Agent(
                    user_id=user.id,
                    active_submission_id=active_sub_id,
                    stats={"rating": 1500, "matches_played": 0}
                )
                session.add(agent)
                session.commit()
                print(f"Created Agent {agent.id}")

        print("Database seeding complete.")


if __name__ == "__main__":
    seed()

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.api.repositories.job import JobRepository
from app.api.repositories.match import MatchRepository
from app.api.repositories.submission import SubmissionRepository
from app.models.game import GameType
from app.models.job import BuildJob, JobStatus, MatchJob
from app.models.match import Match, MatchStatus
from app.models.submission import Submission
from app.models.user import User


@pytest.fixture
def job_repository(db_session: Session):
    return JobRepository(db_session)


@pytest.fixture
def submission_repository(db_session: Session):
    return SubmissionRepository(db_session)


@pytest.fixture
def match_repository(db_session: Session):
    return MatchRepository(db_session)


@pytest.mark.anyio
async def test_build_job_flow(
    api_client: AsyncClient,
    job_repository: JobRepository,
    submission_repository: SubmissionRepository,
    db_session: Session,
):
    # 1. Setup Data
    user = User(email="test@example.com", username="testuser", password_hash="hash")  # noqa: S106
    db_session.add(user)
    db_session.commit()

    submission = Submission(user_id=user.id, name="test_sub", object_path="path/to/zip")
    submission = submission_repository.save(submission)

    job = BuildJob(submission_id=submission.id, status=JobStatus.QUEUED)
    job = job_repository.save_build_job(job)

    # 2. Test GET
    response = await api_client.get(f"/api/v1/jobs/build/{job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(job.id)
    assert data["status"] == "queued"

    # 3. Test UPDATE (Worker reports success)
    update_payload = {
        "status": "completed",
        "logs": "Build successful",
        "image_id": "sha256:12345",
        "image_tag": "latest",
    }
    response = await api_client.patch(f"/api/v1/jobs/build/{job.id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["logs"] == "Build successful\n"

    # 4. Verify Update Job
    db_session.refresh(job)
    assert job.status == "completed"
    assert job.image_id == "sha256:12345"


@pytest.mark.anyio
async def test_match_job_flow(
    api_client: AsyncClient,
    job_repository: JobRepository,
    match_repository: MatchRepository,
    db_session: Session,
):
    # 1. Setup Data
    match = Match(game_type=GameType.TICTACTOE, config={"players": []}, status=MatchStatus.QUEUED)
    match = match_repository.save(match)

    job = MatchJob(match_id=match.id, status=JobStatus.QUEUED)
    job = job_repository.save_match_job(job)

    # 2. Test GET
    response = await api_client.get(f"/api/v1/jobs/match/{job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(job.id)
    assert data["status"] == "queued"

    # 3. Test UPDATE (Worker reports success)
    update_payload = {"status": "completed", "logs": "Match finished", "result": {"winner": "player1"}}
    response = await api_client.patch(f"/api/v1/jobs/match/{job.id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["result"] == {"winner": "player1"}
    assert data["logs"] == "Match finished\n"

    # 4. Verify Sync with Match
    db_session.refresh(match)
    assert match.status == MatchStatus.COMPLETED
    assert match.result == {"winner": "player1"}

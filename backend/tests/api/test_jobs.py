import uuid

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.api.repositories.arena import ArenaRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.match import MatchRepository
from app.api.repositories.submission import SubmissionRepository
from app.core.config import settings
from app.models.arena import Arena
from app.models.game import GameType
from app.models.job import BuildJob, JobStatus, MatchJob
from app.models.match import Match, MatchStatus
from app.models.submission import Submission
from app.models.user import User


# Worker endpoints require the worker API key.
WORKER_HEADERS = {"x-api-key": settings.WORKER_API_KEY}


@pytest.fixture
def job_repository(db_session: Session):
    return JobRepository(db_session)


@pytest.fixture
def submission_repository(db_session: Session):
    return SubmissionRepository(db_session)


@pytest.fixture
def match_repository(db_session: Session):
    return MatchRepository(db_session)


def _get_or_create_test_arena(db_session: Session, game_type: GameType) -> Arena:
    repo = ArenaRepository(db_session)
    arena = db_session.exec(select(Arena).where(Arena.game_type == game_type)).first()
    if not arena:
        arena = Arena(
            id=uuid.uuid4(),
            name=f"Test Arena {game_type.name}",
            game_type=game_type,
            config={},
            is_active=True,
        )
        arena = repo.save(arena)
    return arena


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

    arena = _get_or_create_test_arena(db_session, GameType.TICTACTOE)
    submission = Submission(
        user_id=user.id,
        name="test_sub",
        game_type=GameType.TICTACTOE,
        arena_id=arena.id,
        object_path="path/to/zip",
    )
    submission = submission_repository.save(submission)

    job = BuildJob(submission_id=submission.id, status=JobStatus.QUEUED)
    job = job_repository.save_build_job(job)

    # 2. Test GET
    response = await api_client.get(f"/api/v1/jobs/build/{job.id}", headers=WORKER_HEADERS)
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
    response = await api_client.patch(f"/api/v1/jobs/build/{job.id}", json=update_payload, headers=WORKER_HEADERS)
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
    arena = _get_or_create_test_arena(db_session, GameType.TICTACTOE)
    match = Match(
        game_type=GameType.TICTACTOE,
        arena_id=arena.id,
        config={"players": []},
        status=MatchStatus.QUEUED,
    )
    match = match_repository.save(match)

    job = MatchJob(match_id=match.id, status=JobStatus.QUEUED)
    job = job_repository.save_match_job(job)

    # 2. Test GET
    response = await api_client.get(f"/api/v1/jobs/match/{job.id}", headers=WORKER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(job.id)
    assert data["status"] == "queued"

    # 3. Test UPDATE (Worker reports success)
    update_payload = {"status": "completed"}
    response = await api_client.patch(f"/api/v1/jobs/match/{job.id}", json=update_payload, headers=WORKER_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"

    # 4. Verify Sync with Match
    db_session.refresh(match)
    assert match.status == MatchStatus.COMPLETED


@pytest.mark.anyio
async def test_oversized_worker_logs_and_game_state_are_capped(
    api_client: AsyncClient,
    match_repository: MatchRepository,
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
):
    """Worker logs truncated; oversized game-state rejected."""
    # Use small caps so the test payloads stay tiny.
    monkeypatch.setattr(settings, "MAX_LOG_APPEND_BYTES", 100)
    monkeypatch.setattr(settings, "MAX_TOTAL_LOG_BYTES", 200)
    monkeypatch.setattr(settings, "MAX_GAME_STATE_BYTES", 500)

    arena = _get_or_create_test_arena(db_session, GameType.TICTACTOE)
    match = Match(
        game_type=GameType.TICTACTOE,
        arena_id=arena.id,
        config={"players": []},
        status=MatchStatus.QUEUED,
    )
    match = match_repository.save(match)

    # Oversized logs are truncated, not rejected.
    resp = await api_client.patch(
        f"/api/v1/matches/{match.id}",
        json={"status": "running", "logs": "x" * 5000},
        headers=WORKER_HEADERS,
    )
    assert resp.status_code == 200
    stored_logs = resp.json()["logs"]
    assert len(stored_logs) < 5000
    assert "truncated" in stored_logs

    # Oversized game-state is rejected with 413.
    resp = await api_client.patch(
        f"/api/v1/matches/{match.id}",
        json={"status": "running", "game_state": {"board": ["y" * 1000]}},
        headers=WORKER_HEADERS,
    )
    assert resp.status_code == 413

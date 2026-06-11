import io
import zipfile
from uuid import UUID

import pytest
from sqlmodel import select

from app.core.config import settings
from app.models.agent import Agent
from app.models.game import GameType
from app.models.job import BuildJob, JobStatus
from app.models.submission import Submission
from tests.api.test_users import _create_member_and_token
from tests.utils import random_email, random_lower_string, random_username, strong_password


API_PREFIX = settings.API_V1_PREFIX


def _make_zip_bytes(filename: str = "agent.py", content: str = "print('hello')\n") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        zip_file.writestr(filename, content)
    buffer.seek(0)
    return buffer.getvalue()


@pytest.mark.anyio
async def test_pagination_limit_is_capped(api_client, fake_email_client, db_session):
    """List endpoints reject unbounded limit and negative skip."""
    _, bearer_token = await _create_member_and_token(
        api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
    )
    headers = {"Authorization": bearer_token}

    # An oversized limit is rejected across every paginated list endpoint.
    for path in ("/submissions", "/agents", "/matches", "/agent_containers"):
        resp = await api_client.get(f"{API_PREFIX}{path}?limit=1000000", headers=headers)
        assert resp.status_code == 422, f"{path} should reject limit=1000000"

    # The leaderboard limit is bounded too.
    leaderboard = await api_client.get(
        f"{API_PREFIX}/agents/leaderboard/{GameType.TICTACTOE.value}?limit=1000000", headers=headers
    )
    assert leaderboard.status_code == 422

    # A negative skip is rejected.
    negative_skip = await api_client.get(f"{API_PREFIX}/submissions?skip=-1", headers=headers)
    assert negative_skip.status_code == 422

    # A valid in-range limit still works.
    ok = await api_client.get(f"{API_PREFIX}/submissions?limit=50&skip=0", headers=headers)
    assert ok.status_code == 200


@pytest.mark.anyio
async def test_submission_upload_does_not_create_agent(api_client, fake_email_client, db_session):
    user_id, bearer_token = await _create_member_and_token(
        api_client,
        fake_email_client,
        db_session,
        random_username(),
        random_email(),
        strong_password(),
    )

    response = await api_client.post(
        f"{API_PREFIX}/submissions",
        headers={"Authorization": bearer_token},
        data={"game_type": GameType.CHESS.value},
        files={"file": ("agent.zip", _make_zip_bytes(), "application/zip")},
    )

    assert response.status_code == 201
    submission = response.json()
    assert "build_jobs" in submission
    assert submission["game_type"] == GameType.CHESS.value
    # Scoped to this user: other tests in the session may have created agents.
    assert db_session.exec(select(Agent).where(Agent.user_id == UUID(user_id))).all() == []


@pytest.mark.anyio
async def test_agent_requires_successful_submission_and_submission_delete_unlinks_agent(
    api_client,
    fake_email_client,
    db_session,
):
    user_id, bearer_token = await _create_member_and_token(
        api_client,
        fake_email_client,
        db_session,
        random_username(),
        random_email(),
        strong_password(),
    )

    create_submission_response = await api_client.post(
        f"{API_PREFIX}/submissions",
        headers={"Authorization": bearer_token},
        data={"game_type": GameType.TICTACTOE.value},
        files={"file": ("agent.zip", _make_zip_bytes(), "application/zip")},
    )
    assert create_submission_response.status_code == 201
    submission_id = create_submission_response.json()["id"]

    create_agent_response = await api_client.post(
        f"{API_PREFIX}/agents",
        headers={"Authorization": bearer_token},
        json={
            "name": random_lower_string(8),
            "user_id": user_id,
            "game_type": GameType.TICTACTOE.value,
            "active_submission_id": submission_id,
        },
    )
    assert create_agent_response.status_code == 400
    assert "successfully built" in create_agent_response.json()["detail"]

    submission_uuid = UUID(submission_id)
    build_job = db_session.exec(select(BuildJob).where(BuildJob.submission_id == submission_uuid)).first()
    assert build_job is not None
    build_job.status = JobStatus.COMPLETED
    build_job.image_id = "sha256:test"
    build_job.image_tag = "agent:test"
    db_session.add(build_job)
    db_session.commit()

    create_agent_response = await api_client.post(
        f"{API_PREFIX}/agents",
        headers={"Authorization": bearer_token},
        json={
            "name": random_lower_string(8),
            "user_id": user_id,
            "game_type": GameType.TICTACTOE.value,
            "active_submission_id": submission_id,
        },
    )
    assert create_agent_response.status_code == 201
    agent_id = create_agent_response.json()["id"]

    mismatched_submission_response = await api_client.post(
        f"{API_PREFIX}/submissions",
        headers={"Authorization": bearer_token},
        data={"game_type": GameType.CHESS.value},
        files={"file": ("agent.zip", _make_zip_bytes(), "application/zip")},
    )
    assert mismatched_submission_response.status_code == 201
    mismatched_submission_id = mismatched_submission_response.json()["id"]

    mismatched_build_job = db_session.exec(
        select(BuildJob).where(BuildJob.submission_id == UUID(mismatched_submission_id))
    ).first()
    assert mismatched_build_job is not None
    mismatched_build_job.status = JobStatus.COMPLETED
    mismatched_build_job.image_id = "sha256:mismatched"
    mismatched_build_job.image_tag = "agent:mismatched"
    db_session.add(mismatched_build_job)
    db_session.commit()

    switch_agent_response = await api_client.patch(
        f"{API_PREFIX}/agents/{agent_id}",
        headers={"Authorization": bearer_token},
        json={"active_submission_id": mismatched_submission_id},
    )
    assert switch_agent_response.status_code == 400
    assert "does not match the agent game" in switch_agent_response.json()["detail"]

    delete_submission_response = await api_client.delete(
        f"{API_PREFIX}/submissions/{submission_id}",
        headers={"Authorization": bearer_token},
    )
    assert delete_submission_response.status_code == 204

    agent = db_session.exec(select(Agent).where(Agent.id == UUID(agent_id))).first()
    assert agent is not None
    assert agent.active_submission_id is None


@pytest.mark.anyio
async def test_match_rejects_agent_from_wrong_game(api_client, fake_email_client, db_session):
    user_id, bearer_token = await _create_member_and_token(
        api_client,
        fake_email_client,
        db_session,
        random_username(),
        random_email(),
        strong_password(),
    )

    submission_ids: list[str] = []
    for _ in range(2):
        response = await api_client.post(
            f"{API_PREFIX}/submissions",
            headers={"Authorization": bearer_token},
            data={"game_type": GameType.CHESS.value},
            files={"file": ("agent.zip", _make_zip_bytes(), "application/zip")},
        )
        assert response.status_code == 201
        submission_ids.append(response.json()["id"])

    for submission_id in submission_ids:
        build_job = db_session.exec(select(BuildJob).where(BuildJob.submission_id == UUID(submission_id))).first()
        assert build_job is not None
        build_job.status = JobStatus.COMPLETED
        build_job.image_id = f"sha256:{submission_id}"
        build_job.image_tag = f"agent:{submission_id}"
        db_session.add(build_job)
    db_session.commit()

    agent_ids: list[str] = []
    for submission_id in submission_ids:
        response = await api_client.post(
            f"{API_PREFIX}/agents",
            headers={"Authorization": bearer_token},
            json={
                "name": f"Agent {submission_id[:8]}",
                "user_id": user_id,
                "game_type": GameType.CHESS.value,
                "active_submission_id": submission_id,
            },
        )
        assert response.status_code == 201
        agent_ids.append(response.json()["id"])

    match_response = await api_client.post(
        f"{API_PREFIX}/matches",
        headers={"Authorization": bearer_token},
        json={
            "game_type": GameType.TICTACTOE.value,
            "config": {},
            "agent_ids": agent_ids,
        },
    )
    assert match_response.status_code == 400
    assert "does not belong to game" in match_response.json()["detail"]


async def _make_built_agent(api_client, db_session, bearer_token: str, user_id: str, game_type: GameType) -> str:
    """Create a submission, mark its build completed, and return a built agent's id."""
    headers = {"Authorization": bearer_token}
    sub_resp = await api_client.post(
        f"{API_PREFIX}/submissions",
        headers=headers,
        data={"game_type": game_type.value},
        files={"file": ("agent.zip", _make_zip_bytes(), "application/zip")},
    )
    assert sub_resp.status_code == 201, sub_resp.text
    submission_id = sub_resp.json()["id"]

    build_job = db_session.exec(select(BuildJob).where(BuildJob.submission_id == UUID(submission_id))).first()
    assert build_job is not None
    build_job.status = JobStatus.COMPLETED
    build_job.image_id = f"sha256:{submission_id}"
    build_job.image_tag = f"agent:{submission_id}"
    db_session.add(build_job)
    db_session.commit()

    agent_resp = await api_client.post(
        f"{API_PREFIX}/agents",
        headers=headers,
        json={
            "name": f"Agent {submission_id[:8]}",
            "user_id": user_id,
            "game_type": game_type.value,
            "active_submission_id": submission_id,
        },
    )
    assert agent_resp.status_code == 201, agent_resp.text
    return agent_resp.json()["id"]


@pytest.mark.anyio
async def test_match_state_init_data_is_whitelisted(api_client, fake_email_client, db_session):
    """State_init_data is whitelisted per game before queueing."""
    user_id, bearer_token = await _create_member_and_token(
        api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
    )
    headers = {"Authorization": bearer_token}

    ttt_agents = [
        await _make_built_agent(api_client, db_session, bearer_token, user_id, GameType.TICTACTOE) for _ in range(2)
    ]

    async def _create(config: dict) -> int:
        resp = await api_client.post(
            f"{API_PREFIX}/matches",
            headers=headers,
            json={"game_type": GameType.TICTACTOE.value, "config": config, "agent_ids": ttt_agents},
        )
        return resp.status_code

    # Unknown key -> rejected.
    assert await _create({"state_init_data": {"board_size": 9999}}) == 400
    assert await _create({"state_init_data": {"evil": 1}}) == 400
    # Out-of-range turn/status -> rejected.
    assert await _create({"state_init_data": {"turn": 5}}) == 400
    assert await _create({"state_init_data": {"status": 99}}) == 400
    # Wrong type (passes the dict schema, caught by the whitelist) -> rejected.
    assert await _create({"state_init_data": {"turn": "x"}}) == 400

    # A normal tic-tac-toe match (empty + valid init) still queues.
    assert await _create({}) == 201
    assert await _create({"state_init_data": {"turn": 1, "status": -1}}) == 201

    # Hex: an out-of-range board_size is rejected while a sane one queues.
    hex_agents = [
        await _make_built_agent(api_client, db_session, bearer_token, user_id, GameType.HEX) for _ in range(2)
    ]

    over = await api_client.post(
        f"{API_PREFIX}/matches",
        headers=headers,
        json={
            "game_type": GameType.HEX.value,
            "config": {"state_init_data": {"board_size": 100000}},
            "agent_ids": hex_agents,
        },
    )
    assert over.status_code == 400
    assert "board_size" in over.json()["detail"]

    ok = await api_client.post(
        f"{API_PREFIX}/matches",
        headers=headers,
        json={
            "game_type": GameType.HEX.value,
            "config": {"state_init_data": {"board_size": 11}},
            "agent_ids": hex_agents,
        },
    )
    assert ok.status_code == 201, ok.text


def _make_zip_of_size(min_bytes: int) -> bytes:
    """Build a valid ZIP whose total bytes exceed min_bytes (stored, uncompressed)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as zip_file:
        zip_file.writestr("agent.py", b"A" * min_bytes)
    return buffer.getvalue()


@pytest.mark.anyio
async def test_upload_rejects_oversized_file(api_client, fake_email_client, db_session, monkeypatch):
    """Oversized uploads are rejected."""
    _user_id, bearer_token = await _create_member_and_token(
        api_client,
        fake_email_client,
        db_session,
        random_username(),
        random_email(),
        strong_password(),
    )

    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 1024)
    big_zip = _make_zip_of_size(4096)

    response = await api_client.post(
        f"{API_PREFIX}/submissions",
        headers={"Authorization": bearer_token},
        data={"game_type": GameType.TICTACTOE.value},
        files={"file": ("agent.zip", big_zip, "application/zip")},
    )

    assert response.status_code == 400
    assert "maximum allowed size" in response.json()["detail"]


@pytest.mark.anyio
async def test_download_path_is_contained_to_submissions_dir(api_client, fake_email_client, db_session):
    """Corrupted/traversal object_path is contained within SUBMISSIONS_DIR."""
    _owner_id, bearer_token = await _create_member_and_token(
        api_client,
        fake_email_client,
        db_session,
        random_username(),
        random_email(),
        strong_password(),
    )

    create_response = await api_client.post(
        f"{API_PREFIX}/submissions",
        headers={"Authorization": bearer_token},
        data={"game_type": GameType.TICTACTOE.value},
        files={"file": ("agent.zip", _make_zip_bytes(), "application/zip")},
    )
    assert create_response.status_code == 201
    submission_id = create_response.json()["id"]

    # The stored object_path must be a relative key, not an absolute path.
    submission = db_session.exec(
        select(Submission).where(Submission.id == UUID(submission_id))
    ).first()
    assert submission is not None
    assert submission.object_path == f"{submission_id}.zip"

    # Happy path: the owner can download the real file.
    ok = await api_client.get(
        f"{API_PREFIX}/submissions/{submission_id}/download",
        headers={"Authorization": bearer_token},
    )
    assert ok.status_code == 200

    # Corrupt the path to point outside the submissions dir; download must NOT
    # disclose that file (resolves to a basename under SUBMISSIONS_DIR -> 404).
    submission.object_path = "../../../../../../etc/passwd"
    db_session.add(submission)
    db_session.commit()

    escaped = await api_client.get(
        f"{API_PREFIX}/submissions/{submission_id}/download",
        headers={"Authorization": bearer_token},
    )
    assert escaped.status_code == 404
    assert b"root:" not in escaped.content

import io
import zipfile
from uuid import UUID

import pytest
from sqlmodel import select

from app.core.config import settings
from app.models.agent import Agent
from app.models.game import GameType
from app.models.job import BuildJob, JobStatus
from tests.api.test_users import _create_verified_user_and_token
from tests.utils import random_email, random_username, strong_password


API_PREFIX = settings.API_V1_PREFIX


def _make_zip_bytes(filename: str = "agent.py", content: str = "print('hello')\n") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        zip_file.writestr(filename, content)
    buffer.seek(0)
    return buffer.getvalue()


@pytest.mark.anyio
async def test_submission_upload_does_not_create_agent(api_client, fake_email_client, db_session):
    _, bearer_token = await _create_verified_user_and_token(
        api_client,
        fake_email_client,
        random_username(),
        random_email(),
        strong_password(),
    )

    response = await api_client.post(
        f"{API_PREFIX}/submissions",
        headers={"Authorization": bearer_token},
        files={"file": ("agent.zip", _make_zip_bytes(), "application/zip")},
    )

    assert response.status_code == 201
    submission = response.json()
    assert "build_jobs" in submission
    assert db_session.exec(select(Agent)).all() == []


@pytest.mark.anyio
async def test_agent_requires_successful_submission_and_submission_delete_unlinks_agent(
    api_client,
    fake_email_client,
    db_session,
):
    user_id, bearer_token = await _create_verified_user_and_token(
        api_client,
        fake_email_client,
        random_username(),
        random_email(),
        strong_password(),
    )

    create_submission_response = await api_client.post(
        f"{API_PREFIX}/submissions",
        headers={"Authorization": bearer_token},
        files={"file": ("agent.zip", _make_zip_bytes(), "application/zip")},
    )
    assert create_submission_response.status_code == 201
    submission_id = create_submission_response.json()["id"]

    create_agent_response = await api_client.post(
        f"{API_PREFIX}/agents",
        headers={"Authorization": bearer_token},
        json={
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
            "user_id": user_id,
            "game_type": GameType.TICTACTOE.value,
            "active_submission_id": submission_id,
        },
    )
    assert create_agent_response.status_code == 201
    agent_id = create_agent_response.json()["id"]

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
    user_id, bearer_token = await _create_verified_user_and_token(
        api_client,
        fake_email_client,
        random_username(),
        random_email(),
        strong_password(),
    )

    submission_ids: list[str] = []
    for _ in range(2):
        response = await api_client.post(
            f"{API_PREFIX}/submissions",
            headers={"Authorization": bearer_token},
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

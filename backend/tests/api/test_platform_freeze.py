"""Submission-freeze tests: admin toggle authz + enforcement on mutation routes."""

import uuid

import pytest
from sqlmodel import Session, select

from app.api.repositories.agent import AgentRepository
from app.api.repositories.arena import ArenaRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.submission import SubmissionRepository
from app.core.config import settings
from app.models.agent import Agent
from app.models.arena import Arena
from app.models.game import GameType
from app.models.job import BuildJob, JobStatus
from app.models.submission import Submission
from tests.api.test_users import _create_admin_and_token, _create_member_and_token
from tests.utils import random_email, random_lower_string, random_username, strong_password


API = settings.API_V1_PREFIX
FREEZE_URL = f"{API}/platform/submission-freeze"


async def _member(api_client, fake_email_client, db_session) -> tuple[str, dict]:
    user_id, token = await _create_member_and_token(
        api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
    )
    return user_id, {"Authorization": token}


async def _admin(api_client, fake_email_client, db_session) -> tuple[str, dict]:
    user_id, token = await _create_admin_and_token(
        api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
    )
    return user_id, {"Authorization": token}


def _get_or_create_test_arena(db_session: Session, game_type: GameType) -> Arena:
    repo = ArenaRepository(db_session)
    arena = db_session.exec(select(Arena).where(Arena.game_type == game_type)).first()
    if not arena:
        config = {}
        if game_type == GameType.HEX:
            config = {"board_size": 11}
        elif game_type == GameType.TICTACTOE:
            config = {"turn_time_limit": 5.0}
        arena = Arena(
            id=uuid.uuid4(),
            name=f"Test Arena {game_type.name}",
            game_type=game_type,
            config=config,
            is_active=True,
        )
        arena = repo.save(arena)
    return arena


def _built_submission(db_session: Session, user_id: str) -> Submission:
    arena = _get_or_create_test_arena(db_session, GameType.TICTACTOE)
    submission = SubmissionRepository(db_session).save(
        Submission(
            user_id=uuid.UUID(user_id),
            name=random_lower_string(8),
            game_type=GameType.TICTACTOE,
            arena_id=arena.id,
            object_path="path/to/zip",
        )
    )
    JobRepository(db_session).save_build_job(
        BuildJob(
            submission_id=submission.id,
            status=JobStatus.COMPLETED,
            image_id="sha256:test",
            image_tag=f"agent:{submission.id}",
        )
    )
    db_session.refresh(submission)
    return submission


def _agent(db_session: Session, user_id: str, submission: Submission | None = None) -> Agent:
    arena = _get_or_create_test_arena(db_session, GameType.TICTACTOE)
    return AgentRepository(db_session).save(
        Agent(
            user_id=uuid.UUID(user_id),
            name=random_lower_string(8),
            game_type=GameType.TICTACTOE,
            arena_id=arena.id,
            active_submission_id=submission.id if submission else None,
        )
    )


async def _set_freeze(api_client, admin_headers: dict, enabled: bool) -> None:
    response = await api_client.put(FREEZE_URL, headers=admin_headers, json={"enabled": enabled})
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# Toggle authorization
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_freeze_defaults_off_and_admin_can_toggle(api_client, fake_email_client, db_session):
    _, admin_headers = await _admin(api_client, fake_email_client, db_session)

    response = await api_client.get(FREEZE_URL, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["enabled"] is False

    await _set_freeze(api_client, admin_headers, True)
    response = await api_client.get(FREEZE_URL, headers=admin_headers)
    assert response.json()["enabled"] is True

    await _set_freeze(api_client, admin_headers, False)
    response = await api_client.get(FREEZE_URL, headers=admin_headers)
    assert response.json()["enabled"] is False


@pytest.mark.anyio
async def test_only_admin_can_set_freeze_but_anyone_verified_can_read(api_client, fake_email_client, db_session):
    _, member_headers = await _member(api_client, fake_email_client, db_session)

    # A verified member may read the state (needed for the UI banner)...
    assert (await api_client.get(FREEZE_URL, headers=member_headers)).status_code == 200
    # ...but not change it.
    response = await api_client.put(FREEZE_URL, headers=member_headers, json={"enabled": True})
    assert response.status_code == 403


@pytest.mark.anyio
async def test_anonymous_denied_on_freeze_routes(api_client):
    assert (await api_client.get(FREEZE_URL)).status_code in (401, 403)
    assert (await api_client.put(FREEZE_URL, json={"enabled": True})).status_code in (401, 403)


# ---------------------------------------------------------------------------
# Enforcement on mutation routes
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_freeze_blocks_member_mutations(api_client, fake_email_client, db_session):
    member_id, member_headers = await _member(api_client, fake_email_client, db_session)
    _, admin_headers = await _admin(api_client, fake_email_client, db_session)

    submission = _built_submission(db_session, member_id)
    other_submission = _built_submission(db_session, member_id)
    agent = _agent(db_session, member_id, submission)

    await _set_freeze(api_client, admin_headers, True)

    # Create agent — blocked.
    create = await api_client.post(
        f"{API}/agents",
        headers=member_headers,
        json={"user_id": member_id, "game_type": "tictactoe", "name": "frozen-agent"},
    )
    assert create.status_code == 403
    assert "frozen" in create.json()["detail"].lower()

    # Change active submission — blocked.
    swap = await api_client.patch(
        f"{API}/agents/{agent.id}",
        headers=member_headers,
        json={"active_submission_id": str(other_submission.id)},
    )
    assert swap.status_code == 403

    # Rename only — still allowed (not a code change).
    rename = await api_client.patch(f"{API}/agents/{agent.id}", headers=member_headers, json={"name": "renamed"})
    assert rename.status_code == 200

    # Delete agent / submission — blocked.
    assert (await api_client.delete(f"{API}/agents/{agent.id}", headers=member_headers)).status_code == 403
    assert (
        await api_client.delete(f"{API}/submissions/{other_submission.id}", headers=member_headers)
    ).status_code == 403


@pytest.mark.anyio
async def test_admin_is_exempt_while_frozen(api_client, fake_email_client, db_session):
    admin_id, admin_headers = await _admin(api_client, fake_email_client, db_session)
    agent = _agent(db_session, admin_id, _built_submission(db_session, admin_id))

    await _set_freeze(api_client, admin_headers, True)

    arena = _get_or_create_test_arena(db_session, GameType.TICTACTOE)
    create = await api_client.post(
        f"{API}/agents",
        headers=admin_headers,
        json={
            "user_id": admin_id,
            "game_type": "tictactoe",
            "name": "admin-agent",
            "arena_id": str(arena.id),
        },
    )
    assert create.status_code == 201
    assert (await api_client.delete(f"{API}/agents/{agent.id}", headers=admin_headers)).status_code == 204


@pytest.mark.anyio
async def test_unfreezing_restores_member_mutations(api_client, fake_email_client, db_session):
    member_id, member_headers = await _member(api_client, fake_email_client, db_session)
    _, admin_headers = await _admin(api_client, fake_email_client, db_session)
    agent = _agent(db_session, member_id, _built_submission(db_session, member_id))

    await _set_freeze(api_client, admin_headers, True)
    assert (await api_client.delete(f"{API}/agents/{agent.id}", headers=member_headers)).status_code == 403

    await _set_freeze(api_client, admin_headers, False)
    assert (await api_client.delete(f"{API}/agents/{agent.id}", headers=member_headers)).status_code == 204

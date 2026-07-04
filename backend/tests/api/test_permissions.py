"""RBAC / access-control regression tests.

Roles:
- Anonymous: auth lifecycle only. Else 401/403.
- Guest: read-only; may manage own profile/password.
- User: may mutate own agents/submissions; match requires owning at least one agent.
- Admin: user/role management only.
- Worker: x-api-key only (never JWT); limited to worker callbacks and reads.
"""

import uuid
from pathlib import Path

import pytest
from sqlmodel import Session, select
from app.models.arena import Arena
from app.api.repositories.arena import ArenaRepository

from app.api.repositories.agent import AgentRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.match import MatchRepository
from app.api.repositories.submission import SubmissionRepository
from app.core.config import settings
from app.models.agent import Agent
from app.models.game import GameType
from app.models.job import BuildJob, JobStatus, MatchJob
from app.models.match import Match, MatchStatus
from app.models.submission import Submission
from tests.api.test_users import (
    _create_admin_and_token,
    _create_member_and_token,
    _create_verified_user_and_token,
)
from tests.utils import random_email, random_lower_string, random_username, strong_password


API_PREFIX = settings.API_V1_PREFIX
WORKER_HEADERS = {"x-api-key": settings.WORKER_API_KEY}
BAD_WORKER_HEADERS = {"x-api-key": "definitely-not-the-worker-key"}


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


async def _guest(api_client, fake_email_client) -> tuple[str, dict]:
    """Create a verified GUEST and return (user_id, auth headers)."""
    user_id, token = await _create_verified_user_and_token(
        api_client, fake_email_client, random_username(), random_email(), strong_password()
    )
    return user_id, {"Authorization": token}


async def _member(api_client, fake_email_client, db_session) -> tuple[str, dict]:
    """Create a verified USER and return (user_id, auth headers)."""
    user_id, token = await _create_member_and_token(
        api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
    )
    return user_id, {"Authorization": token}


async def _admin(api_client, fake_email_client, db_session) -> tuple[str, dict]:
    """Create a verified ADMIN and return (user_id, auth headers)."""
    user_id, token = await _create_admin_and_token(
        api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
    )
    return user_id, {"Authorization": token}


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


def _make_submission(db_session: Session, user_id: str, tmp_path: Path | None = None) -> Submission:
    object_path = "path/to/zip"
    if tmp_path is not None:
        # Submissions stored relative to SUBMISSIONS_DIR.
        key = f"{uuid.uuid4()}.zip"
        submissions_dir = Path(settings.SUBMISSIONS_DIR)
        submissions_dir.mkdir(parents=True, exist_ok=True)
        (submissions_dir / key).write_bytes(b"PK\x05\x06" + b"\x00" * 18)  # minimal empty zip
        object_path = key
    arena = _get_or_create_test_arena(db_session, GameType.TICTACTOE)
    submission = Submission(
        user_id=uuid.UUID(user_id),
        name=random_lower_string(8),
        game_type=GameType.TICTACTOE,
        arena_id=arena.id,
        object_path=object_path,
    )
    return SubmissionRepository(db_session).save(submission)


def _make_built_submission(db_session: Session, user_id: str) -> Submission:
    submission = _make_submission(db_session, user_id)
    job = BuildJob(
        submission_id=submission.id,
        status=JobStatus.COMPLETED,
        image_id="sha256:test",
        image_tag=f"agent:{submission.id}",
    )
    JobRepository(db_session).save_build_job(job)
    db_session.refresh(submission)
    return submission


def _make_agent(db_session: Session, user_id: str, submission: Submission | None = None) -> Agent:
    arena = _get_or_create_test_arena(db_session, GameType.TICTACTOE)
    agent = Agent(
        user_id=uuid.UUID(user_id),
        name=random_lower_string(8),
        game_type=GameType.TICTACTOE,
        arena_id=arena.id,
        active_submission_id=submission.id if submission else None,
    )
    return AgentRepository(db_session).save(agent)


def _make_match(db_session: Session, agent_ids: list[str] | None = None) -> Match:
    arena = _get_or_create_test_arena(db_session, GameType.TICTACTOE)
    match = Match(
        game_type=GameType.TICTACTOE,
        arena_id=arena.id,
        status=MatchStatus.QUEUED,
        config={"turn_time_limit": 10.0, "state_init_data": {}},
        agent_ids=agent_ids or [],
    )
    return MatchRepository(db_session).save(match)


# ---------------------------------------------------------------------------
# 1. Anonymous deny-by-default on non-lifecycle routes
# ---------------------------------------------------------------------------

SOME_ID = "00000000-0000-0000-0000-000000000001"

ANON_DENIED_ROUTES = [
    ("GET", f"{API_PREFIX}/agents"),
    ("GET", f"{API_PREFIX}/agents/leaderboard/tictactoe"),
    ("GET", f"{API_PREFIX}/agents/{SOME_ID}"),
    ("POST", f"{API_PREFIX}/agents"),
    ("PATCH", f"{API_PREFIX}/agents/{SOME_ID}"),
    ("DELETE", f"{API_PREFIX}/agents/{SOME_ID}"),
    ("GET", f"{API_PREFIX}/submissions"),
    ("POST", f"{API_PREFIX}/submissions"),
    ("GET", f"{API_PREFIX}/submissions/{SOME_ID}"),
    ("GET", f"{API_PREFIX}/submissions/{SOME_ID}/download"),
    ("DELETE", f"{API_PREFIX}/submissions/{SOME_ID}"),
    ("GET", f"{API_PREFIX}/matches"),
    ("POST", f"{API_PREFIX}/matches"),
    ("GET", f"{API_PREFIX}/matches/{SOME_ID}"),
    ("GET", f"{API_PREFIX}/matches/{SOME_ID}/stream"),
    ("PATCH", f"{API_PREFIX}/matches/{SOME_ID}"),
    ("GET", f"{API_PREFIX}/matches/scheduler/config"),
    ("PUT", f"{API_PREFIX}/matches/scheduler/config"),
    ("GET", f"{API_PREFIX}/jobs/build/{SOME_ID}"),
    ("PATCH", f"{API_PREFIX}/jobs/build/{SOME_ID}"),
    ("GET", f"{API_PREFIX}/jobs/match/{SOME_ID}"),
    ("PATCH", f"{API_PREFIX}/jobs/match/{SOME_ID}"),
    ("POST", f"{API_PREFIX}/jobs"),
    ("GET", f"{API_PREFIX}/agent_containers"),
    ("POST", f"{API_PREFIX}/agent_containers/upsert"),
    ("PATCH", f"{API_PREFIX}/agent_containers/{SOME_ID}"),
    ("GET", f"{API_PREFIX}/users/me"),
    ("PATCH", f"{API_PREFIX}/users/me"),
    ("POST", f"{API_PREFIX}/users/change-password"),
    ("GET", f"{API_PREFIX}/users/roles"),
    ("GET", f"{API_PREFIX}/users"),
    ("GET", f"{API_PREFIX}/users/{SOME_ID}"),
    ("PATCH", f"{API_PREFIX}/users/{SOME_ID}/role"),
    ("DELETE", f"{API_PREFIX}/users/{SOME_ID}"),
    ("PATCH", f"{API_PREFIX}/users/{SOME_ID}/verify-email"),
    ("POST", f"{API_PREFIX}/email/{SOME_ID}/resend-verification"),
    ("POST", f"{API_PREFIX}/email/resend-verification"),
    ("GET", f"{API_PREFIX}/email/verification-status"),
]


@pytest.mark.anyio
@pytest.mark.parametrize(("method", "path"), ANON_DENIED_ROUTES)
async def test_anonymous_is_denied_on_non_lifecycle_routes(api_client, method, path):
    response = await api_client.request(method, path)
    assert response.status_code in (401, 403), (
        f"{method} {path} should deny anonymous access, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# 2. Verified guest is read-only but keeps account lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_verified_guest_can_read_app_data(api_client, fake_email_client, db_session):
    _, headers = await _guest(api_client, fake_email_client)
    match = _make_match(db_session)

    for path in [
        f"{API_PREFIX}/agents",
        f"{API_PREFIX}/agents/leaderboard/tictactoe",
        f"{API_PREFIX}/matches",
        f"{API_PREFIX}/matches/{match.id}",
        f"{API_PREFIX}/agent_containers",
        f"{API_PREFIX}/submissions",
        f"{API_PREFIX}/users/me",
    ]:
        response = await api_client.get(path, headers=headers)
        assert response.status_code == 200, f"GET {path} should be readable for a verified guest"


@pytest.mark.anyio
async def test_verified_guest_cannot_mutate_app_data(api_client, fake_email_client, db_session, tmp_path):
    guest_id, headers = await _guest(api_client, fake_email_client)
    # Resources owned by the guest itself: role gate must still deny writes.
    own_submission = _make_submission(db_session, guest_id, tmp_path)
    own_agent = _make_agent(db_session, guest_id)

    attempts = [
        ("POST", f"{API_PREFIX}/agents", {"json": {"name": "x", "user_id": guest_id, "game_type": "tictactoe"}}),
        ("PATCH", f"{API_PREFIX}/agents/{own_agent.id}", {"json": {"name": "renamed"}}),
        ("DELETE", f"{API_PREFIX}/agents/{own_agent.id}", {}),
        (
            "POST",
            f"{API_PREFIX}/submissions",
            {"data": {"game_type": "tictactoe"}, "files": {"file": ("agent.zip", b"zip", "application/zip")}},
        ),
        ("DELETE", f"{API_PREFIX}/submissions/{own_submission.id}", {}),
        (
            "POST",
            f"{API_PREFIX}/matches",
            {"json": {"game_type": "tictactoe", "config": {}, "agent_ids": [str(own_agent.id)]}},
        ),
    ]
    for method, path, kwargs in attempts:
        response = await api_client.request(method, path, headers=headers, **kwargs)
        assert response.status_code == 403, (
            f"{method} {path} must be forbidden for a verified guest, got {response.status_code}"
        )


@pytest.mark.anyio
async def test_verified_guest_can_manage_own_account(api_client, fake_email_client):
    _, headers = await _guest(api_client, fake_email_client)
    # Account-lifecycle exception: profile edit stays available to guests.
    response = await api_client.patch(
        f"{API_PREFIX}/users/me",
        headers=headers,
        json={"username": random_username()},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 3. Cross-user ownership (agents / submissions)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_cross_user_ownership_is_enforced(api_client, fake_email_client, db_session, tmp_path):
    owner_id, _ = await _member(api_client, fake_email_client, db_session)
    _, intruder_headers = await _member(api_client, fake_email_client, db_session)

    submission = _make_submission(db_session, owner_id, tmp_path)
    agent = _make_agent(db_session, owner_id)

    attempts = [
        ("GET", f"{API_PREFIX}/agents/{agent.id}"),
        ("PATCH", f"{API_PREFIX}/agents/{agent.id}"),
        ("DELETE", f"{API_PREFIX}/agents/{agent.id}"),
        ("GET", f"{API_PREFIX}/submissions/{submission.id}"),
        ("GET", f"{API_PREFIX}/submissions/{submission.id}/download"),
        ("DELETE", f"{API_PREFIX}/submissions/{submission.id}"),
    ]
    for method, path in attempts:
        kwargs = {"json": {"name": "stolen"}} if method == "PATCH" else {}
        response = await api_client.request(method, path, headers=intruder_headers, **kwargs)
        assert response.status_code == 403, (
            f"{method} {path} must be forbidden for a non-owner, got {response.status_code}"
        )


# ---------------------------------------------------------------------------
# 4. Admin-only user/role management (non-admin JWT roles get 403)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_user_role_cannot_manage_users(api_client, fake_email_client, db_session):
    target_id, _ = await _guest(api_client, fake_email_client)
    _, member_headers = await _member(api_client, fake_email_client, db_session)

    attempts = [
        ("GET", f"{API_PREFIX}/users"),
        ("GET", f"{API_PREFIX}/users/{target_id}"),
        ("PATCH", f"{API_PREFIX}/users/{target_id}/role"),
        ("DELETE", f"{API_PREFIX}/users/{target_id}"),
        ("PATCH", f"{API_PREFIX}/users/{target_id}/verify-email"),
        ("GET", f"{API_PREFIX}/matches/scheduler/config"),
    ]
    for method, path in attempts:
        kwargs = {"json": {"role": "admin"}} if path.endswith("/role") else {}
        response = await api_client.request(method, path, headers=member_headers, **kwargs)
        assert response.status_code == 403, (
            f"{method} {path} must be admin-only, got {response.status_code} for USER role"
        )


# ---------------------------------------------------------------------------
# 5. Worker callbacks: x-api-key only
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_worker_callbacks_reject_jwt_and_bad_keys(api_client, fake_email_client, db_session):
    guest = await _guest(api_client, fake_email_client)
    member = await _member(api_client, fake_email_client, db_session)
    admin = await _admin(api_client, fake_email_client, db_session)
    submission_owner, _ = member
    submission = _make_submission(db_session, submission_owner)
    build_job = JobRepository(db_session).save_build_job(
        BuildJob(submission_id=submission.id, status=JobStatus.QUEUED)
    )
    match = _make_match(db_session)
    match_job = JobRepository(db_session).save_match_job(MatchJob(match_id=match.id, status=JobStatus.QUEUED))

    callbacks = [
        ("PATCH", f"{API_PREFIX}/jobs/build/{build_job.id}", {"status": "running"}),
        ("PATCH", f"{API_PREFIX}/jobs/match/{match_job.id}", {"status": "running"}),
        ("POST", f"{API_PREFIX}/jobs", {"submission_id": str(submission.id)}),
        ("PATCH", f"{API_PREFIX}/matches/{match.id}", {"status": "running"}),
        (
            "POST",
            f"{API_PREFIX}/agent_containers/upsert",
            {
                "container_id": "c1",
                "agent_id": SOME_ID,
                "status": "running",
                "image": "agent:test",
            },
        ),
        ("PATCH", f"{API_PREFIX}/agent_containers/{SOME_ID}", {"status": "exited"}),
    ]

    jwt_headers = [None, guest[1], member[1], admin[1]]
    for method, path, payload in callbacks:
        for headers in jwt_headers:
            response = await api_client.request(method, path, headers=headers, json=payload)
            assert response.status_code == 403, (
                f"{method} {path} must require the worker key (got {response.status_code} "
                f"with headers={'anon' if headers is None else 'jwt'})"
            )
        response = await api_client.request(method, path, headers=BAD_WORKER_HEADERS, json=payload)
        assert response.status_code == 403, f"{method} {path} accepted an invalid worker key"


@pytest.mark.anyio
async def test_worker_callbacks_succeed_with_valid_key(api_client, fake_email_client, db_session):
    owner_id, _ = await _member(api_client, fake_email_client, db_session)
    submission = _make_submission(db_session, owner_id)
    build_job = JobRepository(db_session).save_build_job(
        BuildJob(submission_id=submission.id, status=JobStatus.QUEUED)
    )
    match = _make_match(db_session)
    match_job = JobRepository(db_session).save_match_job(MatchJob(match_id=match.id, status=JobStatus.QUEUED))

    response = await api_client.patch(
        f"{API_PREFIX}/jobs/build/{build_job.id}",
        headers=WORKER_HEADERS,
        json={"status": "running", "logs": "building..."},
    )
    assert response.status_code == 200

    response = await api_client.patch(
        f"{API_PREFIX}/jobs/match/{match_job.id}",
        headers=WORKER_HEADERS,
        json={"status": "running"},
    )
    assert response.status_code == 200

    response = await api_client.patch(
        f"{API_PREFIX}/matches/{match.id}",
        headers=WORKER_HEADERS,
        json={"status": "running", "logs": "tick"},
    )
    assert response.status_code == 200

    agent = _make_agent(db_session, owner_id)
    response = await api_client.post(
        f"{API_PREFIX}/agent_containers/upsert",
        headers=WORKER_HEADERS,
        json={
            "container_id": f"c-{uuid.uuid4()}",
            "agent_id": str(agent.id),
            "status": "running",
            "image": "agent:test",
        },
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 6. Worker key is not a JWT identity
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_worker_key_cannot_reach_jwt_routes(api_client, fake_email_client):
    target_id, _ = await _guest(api_client, fake_email_client)

    attempts = [
        ("GET", f"{API_PREFIX}/users"),
        ("GET", f"{API_PREFIX}/users/{target_id}"),
        ("PATCH", f"{API_PREFIX}/users/{target_id}/role"),
        ("DELETE", f"{API_PREFIX}/users/{target_id}"),
        ("GET", f"{API_PREFIX}/users/me"),
        ("GET", f"{API_PREFIX}/matches/scheduler/config"),
        ("PUT", f"{API_PREFIX}/matches/scheduler/config"),
        ("POST", f"{API_PREFIX}/agents"),
        ("POST", f"{API_PREFIX}/matches"),
        ("GET", f"{API_PREFIX}/agents"),
        ("GET", f"{API_PREFIX}/submissions"),
        ("GET", f"{API_PREFIX}/matches"),
    ]
    for method, path in attempts:
        kwargs = {"json": {"role": "admin"}} if path.endswith("/role") else {}
        response = await api_client.request(method, path, headers=WORKER_HEADERS, **kwargs)
        assert response.status_code in (401, 403), (
            f"{method} {path} must not be reachable with only the worker key, got {response.status_code}"
        )


@pytest.mark.anyio
async def test_worker_key_can_read_submissions_and_agents(api_client, fake_email_client, db_session, tmp_path):
    """C-2 migration: the worker keeps exactly the reads it needs."""
    owner_id, _ = await _member(api_client, fake_email_client, db_session)
    submission = _make_submission(db_session, owner_id, tmp_path)
    agent = _make_agent(db_session, owner_id)
    match = _make_match(db_session)

    response = await api_client.get(f"{API_PREFIX}/submissions/{submission.id}", headers=WORKER_HEADERS)
    assert response.status_code == 200

    response = await api_client.get(
        f"{API_PREFIX}/submissions/{submission.id}/download", headers=WORKER_HEADERS
    )
    assert response.status_code == 200

    response = await api_client.get(f"{API_PREFIX}/agents/{agent.id}", headers=WORKER_HEADERS)
    assert response.status_code == 200

    response = await api_client.get(f"{API_PREFIX}/matches/{match.id}", headers=WORKER_HEADERS)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 7. Agent stats are not writable through PATCH /agents
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_user_cannot_write_agent_stats(api_client, fake_email_client, db_session):
    owner_id, headers = await _member(api_client, fake_email_client, db_session)
    agent = _make_agent(db_session, owner_id)

    for payload in [
        {"elo": 99999},
        {"wins": 1000},
        {"losses": 0, "draws": 5},
        {"matches_played": 42},
        {"name": "sneaky", "elo": 99999},
    ]:
        response = await api_client.patch(
            f"{API_PREFIX}/agents/{agent.id}",
            headers=headers,
            json=payload,
        )
        assert response.status_code == 422, (
            f"PATCH /agents with stat fields {payload} must be rejected, got {response.status_code}"
        )

    db_session.refresh(agent)
    assert agent.elo is None
    assert agent.wins == 0
    assert agent.losses == 0
    assert agent.matches_played == 0


@pytest.mark.anyio
async def test_match_completion_still_updates_stats(api_client, fake_email_client, db_session):
    """Stats must keep flowing through the internal match-completion path."""
    owner_a, _ = await _member(api_client, fake_email_client, db_session)
    owner_b, _ = await _member(api_client, fake_email_client, db_session)
    agent_a = _make_agent(db_session, owner_a)
    agent_b = _make_agent(db_session, owner_b)
    match = _make_match(db_session, agent_ids=[str(agent_a.id), str(agent_b.id)])

    response = await api_client.patch(
        f"{API_PREFIX}/matches/{match.id}",
        headers=WORKER_HEADERS,
        json={"status": "completed", "result": {"winner": str(agent_a.id)}},
    )
    assert response.status_code == 200

    db_session.refresh(agent_a)
    db_session.refresh(agent_b)
    assert agent_a.wins == 1
    assert agent_a.matches_played == 1
    assert agent_a.elo is not None
    assert agent_b.losses == 1
    assert agent_b.matches_played == 1


# ---------------------------------------------------------------------------
# 8. Match creation requires owning at least one participating agent
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_match_creation_requires_own_agent(api_client, fake_email_client, db_session):
    caller_id, caller_headers = await _member(api_client, fake_email_client, db_session)
    other_id, _ = await _member(api_client, fake_email_client, db_session)

    other_sub_1 = _make_built_submission(db_session, other_id)
    other_sub_2 = _make_built_submission(db_session, other_id)
    other_agent_1 = _make_agent(db_session, other_id, other_sub_1)
    other_agent_2 = _make_agent(db_session, other_id, other_sub_2)

    response = await api_client.post(
        f"{API_PREFIX}/matches",
        headers=caller_headers,
        json={
            "game_type": "tictactoe",
            "config": {},
            "agent_ids": [str(other_agent_1.id), str(other_agent_2.id)],
        },
    )
    assert response.status_code == 403
    assert "belong to you" in response.json()["detail"]

    own_sub = _make_built_submission(db_session, caller_id)
    own_agent = _make_agent(db_session, caller_id, own_sub)

    response = await api_client.post(
        f"{API_PREFIX}/matches",
        headers=caller_headers,
        json={
            "game_type": "tictactoe",
            "config": {},
            "agent_ids": [str(own_agent.id), str(other_agent_1.id)],
        },
    )
    assert response.status_code == 201, response.text


@pytest.mark.anyio
async def test_admin_can_match_any_agents(api_client, fake_email_client, db_session):
    _, admin_headers = await _admin(api_client, fake_email_client, db_session)
    owner_a, _ = await _member(api_client, fake_email_client, db_session)
    owner_b, _ = await _member(api_client, fake_email_client, db_session)

    sub_a = _make_built_submission(db_session, owner_a)
    sub_b = _make_built_submission(db_session, owner_b)
    agent_a = _make_agent(db_session, owner_a, sub_a)
    agent_b = _make_agent(db_session, owner_b, sub_b)

    response = await api_client.post(
        f"{API_PREFIX}/matches",
        headers=admin_headers,
        json={
            "game_type": "tictactoe",
            "config": {},
            "agent_ids": [str(agent_a.id), str(agent_b.id)],
        },
    )
    assert response.status_code == 201, response.text

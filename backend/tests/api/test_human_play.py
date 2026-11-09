"""Human-vs-agent play: starting games, submitting moves, resigning, and the
isolation rules (no stats/ELO, ignored by the auto-scheduler gates)."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from redis import asyncio as aioredis
from sqlmodel import Session

from app.api.repositories.agent import AgentRepository
from app.api.repositories.arena import ArenaRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.match import MatchRepository
from app.api.repositories.submission import SubmissionRepository
from app.api.services.match import MatchService
from app.api.services.match_scheduler import MatchSchedulerService
from app.core.config import settings
from app.core.queue import human_moves_key
from app.core.tasks import BackgroundTaskRunner
from app.main import app
from app.models.agent import Agent
from app.models.game import GameType
from app.models.match import Match, MatchStatus
from app.models.submission import Submission
from tests.api.test_tournaments import _get_or_create_test_arena, _make_built_agent
from tests.api.test_users import (
    _create_admin_and_token,
    _create_member_and_token,
    _create_verified_user_and_token,
)
from tests.utils import random_email, random_lower_string, random_username, strong_password


API_PREFIX = settings.API_V1_PREFIX

pytestmark = pytest.mark.anyio


async def _member(api_client, fake_email_client, db_session) -> tuple[str, dict[str, str]]:
    user_id, token = await _create_member_and_token(
        api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
    )
    return user_id, {"Authorization": token}


def _match_service(db_session: Session) -> MatchService:
    return MatchService(
        MatchRepository(db_session),
        JobRepository(db_session),
        AgentRepository(db_session),
        ArenaRepository(db_session),
    )


def _set_running(db_session: Session, match_id: str, turn: int) -> None:
    match = db_session.get(Match, uuid.UUID(match_id))
    match.status = MatchStatus.RUNNING
    match.game_state = {"board": [-1] * 9, "turn": turn, "status": -1}
    match.updated_at = datetime.now(UTC)
    db_session.add(match)
    db_session.commit()


async def _pop_human_inputs(match_id: str) -> list[dict]:
    redis = aioredis.from_url(settings.REDIS_URL, encoding="utf8", decode_responses=True)
    try:
        key = human_moves_key(match_id)
        raw = await redis.lrange(key, 0, -1)
        await redis.delete(key)
        return [json.loads(r) for r in raw]
    finally:
        await redis.aclose()


async def _start_game(api_client, headers, agent: Agent, seat: int = 0):
    return await api_client.post(
        f"{API_PREFIX}/matches/human",
        json={"arena_id": str(agent.arena_id), "agent_id": str(agent.id), "human_player_index": seat},
        headers=headers,
    )


async def test_human_game_move_flow(api_client, fake_email_client, db_session):
    user_id, headers = await _member(api_client, fake_email_client, db_session)
    agent = _make_built_agent(db_session, GameType.TICTACTOE)  # someone else's agent

    resp = await _start_game(api_client, headers, agent, seat=0)
    assert resp.status_code == 201, resp.text
    match = resp.json()
    match_id = match["id"]
    assert match["agent_ids"] == [str(agent.id)]
    assert match["human_user_id"] == user_id
    assert match["human_player_index"] == 0
    assert match["config"]["human_turn_time_limit"] == settings.HUMAN_MOVE_TIME_LIMIT_SECONDS
    assert match["config"]["max_duration_seconds"] == settings.HUMAN_MATCH_MAX_DURATION_SECONDS

    # One active human game per user.
    second = await _start_game(api_client, headers, agent)
    assert second.status_code == 409

    # Not running yet.
    resp = await api_client.post(
        f"{API_PREFIX}/matches/{match_id}/human-move", json={"move": {"position": 4}}, headers=headers
    )
    assert resp.status_code == 409

    # Running and the human's turn: the move is forwarded with the seat filled in.
    _set_running(db_session, match_id, turn=0)
    resp = await api_client.post(
        f"{API_PREFIX}/matches/{match_id}/human-move",
        json={"move": {"position": 4, "player": 1}},  # a spoofed player is overwritten
        headers=headers,
    )
    assert resp.status_code == 202, resp.text
    assert await _pop_human_inputs(match_id) == [{"type": "move", "move": {"position": 4, "player": 0}}]

    # Agent's turn: rejected.
    _set_running(db_session, match_id, turn=1)
    resp = await api_client.post(
        f"{API_PREFIX}/matches/{match_id}/human-move", json={"move": {"position": 5}}, headers=headers
    )
    assert resp.status_code == 409

    # Someone else can't move or resign for the human.
    _, other_headers = await _member(api_client, fake_email_client, db_session)
    _set_running(db_session, match_id, turn=0)
    resp = await api_client.post(
        f"{API_PREFIX}/matches/{match_id}/human-move", json={"move": {"position": 5}}, headers=other_headers
    )
    assert resp.status_code == 403
    resp = await api_client.post(f"{API_PREFIX}/matches/{match_id}/resign", headers=other_headers)
    assert resp.status_code == 403

    # Oversized move payloads are refused.
    resp = await api_client.post(
        f"{API_PREFIX}/matches/{match_id}/human-move", json={"move": {"x": "a" * 5000}}, headers=headers
    )
    assert resp.status_code == 413

    # Resigning a running game hands the resignation to the worker.
    resp = await api_client.post(f"{API_PREFIX}/matches/{match_id}/resign", headers=headers)
    assert resp.status_code == 200
    assert await _pop_human_inputs(match_id) == [{"type": "resign"}]


async def test_cancel_queued_game_frees_the_slot(api_client, fake_email_client, db_session):
    username = random_username()
    user_id, token = await _create_member_and_token(
        api_client, fake_email_client, db_session, username, random_email(), strong_password()
    )
    headers = {"Authorization": token}
    agent = _make_built_agent(db_session, GameType.TICTACTOE)

    match_id = (await _start_game(api_client, headers, agent)).json()["id"]
    resp = await api_client.post(f"{API_PREFIX}/matches/{match_id}/resign", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == MatchStatus.FAILED.value

    # Already over.
    resp = await api_client.post(f"{API_PREFIX}/matches/{match_id}/resign", headers=headers)
    assert resp.status_code == 409

    # A worker that picked the game up meanwhile can't revive it.
    revived = await _match_service(db_session).update_match(match_id, status=MatchStatus.RUNNING.value)
    assert revived.status == MatchStatus.FAILED

    # The stream of a finished game sends one event: seats and display names included.
    resp = await api_client.get(f"{API_PREFIX}/matches/{match_id}/stream", headers=headers)
    assert resp.status_code == 200
    event = json.loads(resp.text.removeprefix("data: ").strip())
    assert event["human_user_id"] == user_id
    assert event["human_name"] == username
    assert event["agent_names"] == {str(agent.id): agent.name}

    assert (await _start_game(api_client, headers, agent)).status_code == 201


async def test_stale_running_game_does_not_lock_user_out(api_client, fake_email_client, db_session):
    _, headers = await _member(api_client, fake_email_client, db_session)
    agent = _make_built_agent(db_session, GameType.TICTACTOE)

    stale_at = datetime.now(UTC) - timedelta(seconds=settings.MATCH_STALE_TIMEOUT_SECONDS + 30)
    match_id = (await _start_game(api_client, headers, agent)).json()["id"]
    _set_running(db_session, match_id, turn=0)
    match = db_session.get(Match, uuid.UUID(match_id))
    match.updated_at = stale_at
    # A stale match that isn't this user's human game is left to the schedulers.
    other = Match(
        game_type=agent.game_type,
        arena_id=agent.arena_id,
        status=MatchStatus.RUNNING,
        agent_ids=[str(agent.id)],
        updated_at=stale_at,
    )
    db_session.add_all([match, other])
    db_session.commit()

    assert (await _start_game(api_client, headers, agent)).status_code == 201
    db_session.refresh(match)
    db_session.refresh(other)
    assert match.status == MatchStatus.FAILED
    assert other.status == MatchStatus.RUNNING


async def test_guest_cannot_start_human_game(api_client, fake_email_client, db_session):
    _, token = await _create_verified_user_and_token(
        api_client, fake_email_client, random_username(), random_email(), strong_password()
    )
    agent = _make_built_agent(db_session, GameType.TICTACTOE)
    resp = await _start_game(api_client, {"Authorization": token}, agent)
    assert resp.status_code == 403


async def test_human_game_requires_built_agent(api_client, fake_email_client, db_session):
    _, headers = await _member(api_client, fake_email_client, db_session)
    arena = _get_or_create_test_arena(db_session, GameType.TICTACTOE)
    unbuilt = AgentRepository(db_session).save(
        Agent(user_id=uuid.uuid4(), name="unbuilt", game_type=GameType.TICTACTOE, arena_id=arena.id)
    )
    resp = await _start_game(api_client, headers, unbuilt)
    assert resp.status_code == 400


async def test_opponents_lists_any_built_agent(api_client, fake_email_client, db_session):
    user_id, headers = await _member(api_client, fake_email_client, db_session)
    owner_id, _ = await _member(api_client, fake_email_client, db_session)
    arena = _get_or_create_test_arena(db_session, GameType.TICTACTOE)

    def make_agent(owner: str, built: bool) -> Agent:
        submission_id = None
        if built:
            submission_id = _make_built_agent(db_session, GameType.TICTACTOE).active_submission_id
        else:
            submission_id = SubmissionRepository(db_session).save(
                Submission(
                    user_id=uuid.UUID(owner),
                    name=random_lower_string(8),
                    game_type=GameType.TICTACTOE,
                    arena_id=arena.id,
                    object_path="path/to/zip",
                )
            ).id
        return AgentRepository(db_session).save(
            Agent(
                user_id=uuid.UUID(owner),
                name=random_lower_string(8),
                game_type=GameType.TICTACTOE,
                arena_id=arena.id,
                active_submission_id=submission_id,
            )
        )

    mine = make_agent(user_id, built=True)
    theirs = make_agent(owner_id, built=True)
    unbuilt = make_agent(owner_id, built=False)

    resp = await api_client.get(f"{API_PREFIX}/matches/human/opponents?arena_id={arena.id}", headers=headers)
    assert resp.status_code == 200
    by_id = {o["id"]: o for o in resp.json()}
    assert by_id[str(mine.id)]["is_mine"] is True
    assert by_id[str(theirs.id)]["is_mine"] is False
    assert str(unbuilt.id) not in by_id
    # Own agents are listed first.
    assert resp.json()[0]["is_mine"] is True


async def test_human_game_skips_stats_and_scheduler_gates(db_session):
    service = _match_service(db_session)
    agent = _make_built_agent(db_session, GameType.TICTACTOE)
    repo = MatchRepository(db_session)
    active_before = repo.count_active_non_tournament()

    match = await service.create_human_match(
        arena_id=agent.arena_id,
        agent_id=agent.id,
        human_user_id=uuid.uuid4(),
        human_player_index=1,
        human_turn_time_limit=30.0,
        max_duration_seconds=600.0,
    )
    # Ignored by the auto-scheduler's concurrency count and serial gate.
    assert repo.count_active_non_tournament() == active_before
    assert all(m.id != match.id for m in repo.list_matches(0, 100, status="queued", with_human=False))

    await service.update_match(
        str(match.id),
        status=MatchStatus.COMPLETED.value,
        result={"winner": str(agent.id), "scores": {}, "reason": "Game finished"},
    )
    db_session.refresh(agent)
    assert agent.matches_played == 0
    assert agent.wins == 0
    assert agent.elo is None


async def test_regular_match_cannot_set_human_limits(api_client, fake_email_client, db_session):
    user_id, headers = await _member(api_client, fake_email_client, db_session)
    agent_a = _make_built_agent(db_session, GameType.TICTACTOE)
    agent_b = _make_built_agent(db_session, GameType.TICTACTOE)
    agent_a.user_id = uuid.UUID(user_id)
    AgentRepository(db_session).save(agent_a)

    resp = await api_client.post(
        f"{API_PREFIX}/matches",
        json={
            "arena_id": str(agent_a.arena_id),
            "agent_ids": [str(agent_a.id), str(agent_b.id)],
            "config": {"max_duration_seconds": 99999, "human_turn_time_limit": 999},
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["config"]["max_duration_seconds"] is None
    assert resp.json()["config"]["human_turn_time_limit"] is None
    assert resp.json()["human_user_id"] is None


async def test_scheduler_settings_control_human_limits(api_client, fake_email_client, db_session):
    """Admins set the human move/game limits in the scheduler settings; new games use them."""
    # The in-memory test client doesn't run the lifespan; register an (unstarted) runner.
    runner = BackgroundTaskRunner()
    runner.add_task(
        func=MatchSchedulerService().check_and_queue_matches,
        interval_seconds=10.0,
        name="match_scheduler",
        is_enabled=False,
    )
    previous = getattr(app.state, "task_runner", None)
    app.state.task_runner = runner
    try:
        _, admin_token = await _create_admin_and_token(
            api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
        )
        admin = {"Authorization": admin_token}
        config = (await api_client.get(f"{API_PREFIX}/matches/scheduler/config", headers=admin)).json()
        assert config["human_move_time_limit"] == settings.HUMAN_MOVE_TIME_LIMIT_SECONDS
        assert config["human_match_max_duration"] == settings.HUMAN_MATCH_MAX_DURATION_SECONDS

        bad = await api_client.put(
            f"{API_PREFIX}/matches/scheduler/config", json={**config, "human_move_time_limit": 1}, headers=admin
        )
        assert bad.status_code == 422

        resp = await api_client.put(
            f"{API_PREFIX}/matches/scheduler/config",
            json={**config, "human_move_time_limit": 120, "human_match_max_duration": 1800},
            headers=admin,
        )
        assert resp.status_code == 200
        assert resp.json()["human_move_time_limit"] == 120

        _, headers = await _member(api_client, fake_email_client, db_session)
        agent = _make_built_agent(db_session, GameType.TICTACTOE)
        match = (await _start_game(api_client, headers, agent)).json()
        assert match["config"]["human_turn_time_limit"] == 120
        assert match["config"]["max_duration_seconds"] == 1800
    finally:
        if previous is None:
            del app.state.task_runner
        else:
            app.state.task_runner = previous


async def test_human_move_deadline_is_server_side(db_session):
    """The runner reports the deadline; it survives re-reads (page refreshes) and clears on the next state."""
    service = _match_service(db_session)
    agent = _make_built_agent(db_session, GameType.TICTACTOE)
    match = await service.create_human_match(
        arena_id=agent.arena_id,
        agent_id=agent.id,
        human_user_id=uuid.uuid4(),
        human_player_index=0,
        human_turn_time_limit=60.0,
        max_duration_seconds=900.0,
    )
    match_id = str(match.id)
    assert await service.get_human_move_remaining(match) is None  # queued

    state = {"board": [-1] * 9, "turn": 0, "status": -1}
    await service.update_match(match_id, status="running", game_state=state)
    match = await service.update_match(match_id, status="running", human_turn_seconds=60.0)
    remaining = await service.get_human_move_remaining(match)
    assert remaining is not None
    assert 58.0 < remaining <= 60.0

    # A heartbeat doesn't reset it.
    match = await service.update_match(match_id, status="running")
    assert 58.0 < await service.get_human_move_remaining(match) <= remaining

    # The human's move is applied: no pending human move anymore.
    state = {"board": [0] + [-1] * 8, "turn": 1, "status": -1}
    match = await service.update_match(match_id, status="running", game_state=state)
    assert await service.get_human_move_remaining(match) is None

    await service.update_match(match_id, status="running", human_turn_seconds=30.0)
    match = await service.update_match(match_id, status="completed", result={"winner": "human"})
    assert await service.get_human_move_remaining(match) is None

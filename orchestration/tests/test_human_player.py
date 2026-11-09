"""
Human seat in the match loop: moves arrive over Redis, illegal moves are ignored
(not forfeited), and timeouts / resignations end the game for the agent.

Needs a Redis server: set TEST_REDIS_URL (e.g. the backend test stack's
redis://localhost:6380/0); skipped otherwise.
"""

import asyncio
import json
import os
import time
import uuid

import pytest
from gamelib.tictactoe.engine import Engine
from gamelib.tictactoe.gamestate import GameState
from gamelib.tictactoe.move import Move
from redis import asyncio as aioredis

from lib import human_player
from lib.human_player import HumanPlayer, human_moves_key
from lib.match_manager import _parse_match_config, _play_human_turn

REDIS_URL = os.getenv("TEST_REDIS_URL")
pytestmark = pytest.mark.skipif(not REDIS_URL, reason="TEST_REDIS_URL not set")


class FakeAPI:
    def __init__(self) -> None:
        self.logs: list[str] = []
        self.heartbeats = 0
        self.deadlines: list[float] = []

    async def update_match(self, match_id, status, logs=None, human_turn_seconds=None, **_):  # noqa: ANN001, ANN003
        if human_turn_seconds is not None:
            self.deadlines.append(human_turn_seconds)
        elif logs:
            self.logs.append(logs)
        else:
            self.heartbeats += 1


async def _push(match_id: str, *messages: dict) -> None:
    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        for m in messages:
            await redis.rpush(human_moves_key(match_id), json.dumps(m))
    finally:
        await redis.aclose()


async def _turn(match_id: str, api: FakeAPI, *, limit: float = 5.0, wall: float = 60.0):
    human = HumanPlayer(match_id, player_id=0, redis_url=REDIS_URL)
    await human.start()
    try:
        return await _play_human_turn(
            api=api,
            match_id=match_id,
            human=human,
            engine=Engine(),
            state=GameState.initial({}),
            move_cls=Move,
            turn_count=1,
            move_time_limit=limit,
            match_deadline=time.monotonic() + wall,
        )
    finally:
        await human.cleanup()


def test_illegal_moves_are_ignored_until_a_legal_one():
    match_id = str(uuid.uuid4())
    api = FakeAPI()

    async def scenario():
        await _push(
            match_id,
            {"type": "move", "move": {"player": 0, "position": 42}},  # out of range
            {"type": "move", "move": {"player": 0, "position": "4"}},  # wrong type (strict)
            {"type": "bogus"},
            {"type": "move", "move": {"player": 0, "position": 4}},
        )
        return await _turn(match_id, api)

    outcome = asyncio.run(scenario())
    assert outcome.move is not None
    assert outcome.move.position == 4
    assert sum("illegal move ignored" in line for line in api.logs) == 2


def test_resignation_hands_the_win_to_the_agent():
    match_id = str(uuid.uuid4())
    api = FakeAPI()

    async def scenario():
        await _push(match_id, {"type": "resign"})
        return await _turn(match_id, api)

    outcome = asyncio.run(scenario())
    assert outcome.move is None
    assert outcome.reason == "Resigned"
    assert outcome.winner_id == 1


def test_timeout_forfeits_and_heartbeats_while_waiting(monkeypatch):
    monkeypatch.setattr(human_player, "HEARTBEAT_INTERVAL_SECONDS", 0.2)
    api = FakeAPI()
    outcome = asyncio.run(_turn(str(uuid.uuid4()), api, limit=1.0))
    assert outcome.move is None
    assert outcome.reason == "Time limit exceeded"
    assert outcome.winner_id == 1
    assert api.heartbeats >= 2
    assert api.deadlines == [1.0]  # the UI countdown is driven by this report


def test_wall_clock_cap_ends_without_a_winner():
    api = FakeAPI()
    outcome = asyncio.run(_turn(str(uuid.uuid4()), api, limit=30.0, wall=0.5))
    assert outcome.move is None
    assert outcome.reason == "Match wall-clock limit exceeded"
    assert outcome.winner_id == -1
    # The reported deadline is capped by the game's remaining wall-clock time.
    assert len(api.deadlines) == 1
    assert api.deadlines[0] <= 0.5


def test_discard_pending_keeps_resignation():
    match_id = str(uuid.uuid4())

    async def scenario():
        await _push(match_id, {"type": "move", "move": {"player": 0, "position": 1}}, {"type": "resign"})
        human = HumanPlayer(match_id, player_id=0, redis_url=REDIS_URL)
        await human.start()
        try:
            await human.discard_pending()
            redis = aioredis.from_url(REDIS_URL, decode_responses=True)
            try:
                return await redis.lrange(human_moves_key(match_id), 0, -1)
            finally:
                await redis.aclose()
        finally:
            await human.cleanup()

    assert [json.loads(r) for r in asyncio.run(scenario())] == [{"type": "resign"}]


def test_parse_match_config_human_fields():
    cfg = _parse_match_config({"turn_time_limit": 2, "human_turn_time_limit": 45, "max_duration_seconds": 900})
    assert cfg.turn_time_limit == 2
    assert cfg.human_turn_time_limit == 45
    assert cfg.max_duration_seconds == 900

    defaults = _parse_match_config({"human_turn_time_limit": None, "max_duration_seconds": "nope"})
    assert defaults.human_turn_time_limit == 60.0
    assert defaults.max_duration_seconds is None


class FakeAgent:
    """Stands in for AgentProcess: always plays the first empty cell."""

    container_id = None
    stderr_tail = ""

    def __init__(self, image_tag: str, player_id: int) -> None:
        self.player_id = player_id
        self._state: dict | None = None

    def verify_image(self) -> None: ...
    async def start(self) -> None: ...
    async def send_init(self) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    async def cleanup(self) -> None: ...

    async def send_state(self, state_json: str) -> None:
        self._state = json.loads(state_json)

    async def get_move(self, timeout: float | None = None) -> tuple[str, list[str]]:  # noqa: ARG002
        position = self._state["board"].index(-1)
        return json.dumps({"move": {"player": self.player_id, "position": position}, "cpu_time": 0.01}), []


class FakeMatchAPI(FakeAPI):
    def __init__(self, human_index: int) -> None:
        super().__init__()
        self.human_index = human_index
        self.states: list[dict] = []

    async def get_match(self, match_id):  # noqa: ANN001, ARG002
        return {"game_type": "tictactoe", "config": {}, "human_player_index": self.human_index}

    async def update_match(self, match_id, status, logs=None, game_state=None, **_):  # noqa: ANN001, ANN003
        if game_state is not None:
            self.states.append(game_state)
        await super().update_match(match_id, status, logs=logs)

    async def report_container_stats(self, data):  # noqa: ANN001, ARG002
        return {}


def test_full_match_human_beats_agent(monkeypatch):
    """Human (seat 0) plays 4, 2, 6 against a first-empty-cell agent and wins on the 2-4-6 diagonal."""
    from lib import match_manager

    monkeypatch.setattr(match_manager, "AgentProcess", FakeAgent)
    monkeypatch.setenv("REDIS_URL", REDIS_URL)
    match_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    api = FakeMatchAPI(human_index=0)

    async def human_moves() -> None:
        plan = iter([4, 2, 6])
        seen = 0
        while True:
            await asyncio.sleep(0.02)
            if len(api.states) == seen:
                continue
            seen = len(api.states)
            state = api.states[-1]
            if state["status"] != -1:
                return
            if state["turn"] == 0:
                # The backend fills in "player"; this test pushes straight to Redis.
                await _push(match_id, {"type": "move", "move": {"player": 0, "position": next(plan)}})

    async def scenario():
        pusher = asyncio.create_task(human_moves())
        result = await match_manager.run_match(match_id, {}, [agent_id], ["fake:image"], api)
        pusher.cancel()
        return result

    result = asyncio.run(scenario())
    assert result["winner"] == "human", result
    assert result["reason"] == "Game finished"
    assert result["scores"] == {"human": 1, agent_id: 0}
    assert result["history"][-1]["board"] == [1, 1, 0, -1, 0, -1, 0, -1, -1]

"""
Unit tests for the non-tournament match auto-scheduler's concurrency logic.

These cover the pure scheduling math (no DB needed): how many slots to fill to
keep workers busy without overflowing the queue, and how a batch of matches
created in a single tick is spread across agents instead of repeatedly picking
the same least-played pairing.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.services.match_scheduler import (
    SCHEDULING_CONCURRENT,
    SCHEDULING_SERIAL,
    MatchSchedulerService,
)
from app.core.config import settings


def _agent(matches_played: int):
    return SimpleNamespace(id=uuid4(), matches_played=matches_played)


class _ConcurrentStubRepo:
    def __init__(self, in_flight: int) -> None:
        self._in_flight = in_flight

    def count_active_non_tournament(self) -> int:
        return self._in_flight


class _SerialStubRepo:
    """Mimics the queued/running gate the serial strategy consults."""

    def __init__(self, has_queued: bool, has_running: bool) -> None:
        self._has_queued = has_queued
        self._has_running = has_running

    def list_matches(self, *, skip, limit, status, with_tournament):  # noqa: ARG002
        from app.models.match import MatchStatus

        if status == MatchStatus.QUEUED.value:
            return [object()] if self._has_queued else []
        if status == MatchStatus.RUNNING.value:
            return [object()] if self._has_running else []
        return []


def test_default_scheduling_strategy_is_serial():
    # The legacy behaviour must remain the default so existing deployments are unchanged.
    assert MatchSchedulerService().scheduling_strategy == SCHEDULING_SERIAL


def test_serial_strategy_queues_one_at_a_time():
    scheduler = MatchSchedulerService()  # defaults to serial
    # Idle -> queue exactly one.
    assert scheduler._free_slots(_SerialStubRepo(has_queued=False, has_running=False)) == 1
    # Something already queued or running -> queue nothing.
    assert scheduler._free_slots(_SerialStubRepo(has_queued=True, has_running=False)) == 0
    assert scheduler._free_slots(_SerialStubRepo(has_queued=False, has_running=True)) == 0


def test_concurrent_strategy_fills_up_to_target(monkeypatch):
    monkeypatch.setattr(settings, "MATCH_MAX_CONCURRENT_MATCHES", 5)
    scheduler = MatchSchedulerService()
    scheduler.scheduling_strategy = SCHEDULING_CONCURRENT
    # Nothing in flight -> fill all 5 slots (serial would only ever return 1).
    assert scheduler._free_slots(_ConcurrentStubRepo(0)) == 5
    # Partially busy -> top up the remainder.
    assert scheduler._free_slots(_ConcurrentStubRepo(3)) == 2


def test_concurrent_strategy_capped_at_target(monkeypatch):
    monkeypatch.setattr(settings, "MATCH_MAX_CONCURRENT_MATCHES", 4)
    scheduler = MatchSchedulerService()
    scheduler.scheduling_strategy = SCHEDULING_CONCURRENT
    # At or above the target -> no new matches (don't flood the queue).
    assert scheduler._free_slots(_ConcurrentStubRepo(4)) == 0
    assert scheduler._free_slots(_ConcurrentStubRepo(6)) <= 0


def test_choose_agents_spreads_batch_across_agents():
    """A batch built in one tick should not stack on the same least-played pair."""
    scheduler = MatchSchedulerService()
    agents = [_agent(0) for _ in range(4)]

    local_played: dict = {}
    appearances: dict = {a.id: 0 for a in agents}

    # Create two matches as the tick loop would, updating the local tally between.
    for _ in range(2):
        chosen = scheduler._choose_agents_for_match(agents, local_played)
        assert len(chosen) == 2
        assert chosen[0] != chosen[1]
        for agent_id in chosen:
            local_played[agent_id] = local_played.get(agent_id, 0) + 1
            appearances[agent_id] += 1

    # Two matches with four equally-played agents must cover all four exactly once.
    assert all(count == 1 for count in appearances.values())


def test_choose_agents_without_local_tally_picks_least_played():
    scheduler = MatchSchedulerService()
    low_a, low_b = _agent(0), _agent(0)
    high = _agent(100)
    chosen = set(scheduler._choose_agents_for_match([low_a, low_b, high]))
    assert chosen == {low_a.id, low_b.id}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

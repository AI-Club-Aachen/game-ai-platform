# ruff: noqa: S311
"""Unit tests for the pure double-elimination bracket math (no DB)."""

import random
import uuid
from collections import Counter

import pytest

from app.api.services.tournament_bracket import (
    MatchupSpec,
    deterministic_coin_flip,
    game_agent_order,
    generate_double_elimination_bracket,
    next_power_of_two,
)
from app.models.tournament import BracketSide, SlotSourceRole


def _agents(n: int) -> list[uuid.UUID]:
    return [uuid.uuid4() for _ in range(n)]


def _by_key(specs: list[MatchupSpec]) -> dict[tuple[BracketSide, int, int], MatchupSpec]:
    return {(s.bracket, s.round, s.position): s for s in specs}


@pytest.mark.parametrize("n", [35, 39])
def test_bracket_structure_for_non_power_of_two(n: int):
    agents = _agents(n)
    specs = generate_double_elimination_bracket(agents, random.Random(7))

    bracket_size = next_power_of_two(n)  # 64 for both
    rounds = bracket_size.bit_length() - 1  # 6

    # Total matchups in a full double-elimination bracket: 2 * P - 1
    # (P-1 winners, P-2 losers, grand final, grand-final reset).
    assert len(specs) == 2 * bracket_size - 1

    counts = Counter((s.bracket, s.round) for s in specs)
    assert counts[(BracketSide.WINNERS, 1)] == bracket_size // 2
    assert counts[(BracketSide.WINNERS, rounds)] == 1
    assert counts[(BracketSide.LOSERS, 2 * (rounds - 1))] == 1
    assert counts[(BracketSide.GRAND_FINAL, 1)] == 1
    assert counts[(BracketSide.GRAND_FINAL_RESET, 1)] == 1

    # Every entrant appears exactly once in round 1, byes fill the rest.
    round_one = [s for s in specs if s.bracket == BracketSide.WINNERS and s.round == 1]
    placed = [a for s in round_one for a in (s.agent1_id, s.agent2_id) if a is not None]
    assert sorted(placed, key=str) == sorted(agents, key=str)
    byes = sum(1 for s in round_one if s.agent2_id is None)
    assert byes == bracket_size - n


@pytest.mark.parametrize("n", [35, 39])
def test_byes_are_spread_over_distinct_matchups(n: int):
    specs = generate_double_elimination_bracket(_agents(n), random.Random(3))
    round_one = [s for s in specs if s.bracket == BracketSide.WINNERS and s.round == 1]
    # No double-bye: every round-1 matchup has at least one agent.
    assert all(s.agent1_id is not None for s in round_one)


def test_source_links_and_stages_are_consistent():
    specs = generate_double_elimination_bracket(_agents(35), random.Random(11))
    by_id = {s.id: s for s in specs}

    for spec in specs:
        for source in (spec.slot1_source, spec.slot2_source):
            if source is None:
                continue
            src = by_id[source.matchup_id]
            # Round-by-round gating: a matchup only depends on strictly earlier stages.
            assert src.stage < spec.stage

    # Losers-bracket round 1 is fed by winners-bracket round 1 losers.
    lb1 = [s for s in specs if s.bracket == BracketSide.LOSERS and s.round == 1]
    for spec in lb1:
        assert spec.slot1_source.role == SlotSourceRole.LOSER
        assert spec.slot2_source.role == SlotSourceRole.LOSER
        assert by_id[spec.slot1_source.matchup_id].bracket == BracketSide.WINNERS

    # The grand final pairs the winners-bracket champion with the losers-bracket champion.
    gf = next(s for s in specs if s.bracket == BracketSide.GRAND_FINAL)
    wb_final = by_id[gf.slot1_source.matchup_id]
    lb_final = by_id[gf.slot2_source.matchup_id]
    assert (wb_final.bracket, gf.slot1_source.role) == (BracketSide.WINNERS, SlotSourceRole.WINNER)
    assert (lb_final.bracket, gf.slot2_source.role) == (BracketSide.LOSERS, SlotSourceRole.WINNER)

    # The reset matchup replays the grand final participants.
    reset = next(s for s in specs if s.bracket == BracketSide.GRAND_FINAL_RESET)
    assert reset.slot1_source.matchup_id == gf.id
    assert reset.slot2_source.matchup_id == gf.id
    assert reset.stage == gf.stage + 1


def test_two_entrant_bracket_has_no_losers_rounds():
    specs = generate_double_elimination_bracket(_agents(2), random.Random(1))
    brackets = Counter(s.bracket for s in specs)
    assert brackets[BracketSide.WINNERS] == 1
    assert brackets[BracketSide.LOSERS] == 0
    assert brackets[BracketSide.GRAND_FINAL] == 1
    assert brackets[BracketSide.GRAND_FINAL_RESET] == 1

    # The winners final loser feeds the grand final directly.
    gf = next(s for s in specs if s.bracket == BracketSide.GRAND_FINAL)
    assert gf.slot2_source.role == SlotSourceRole.LOSER


def test_generation_rejects_too_few_entrants():
    with pytest.raises(ValueError, match="at least 2"):
        generate_double_elimination_bracket(_agents(1), random.Random(1))


def test_deterministic_coin_flip_is_reproducible_and_balanced():
    matchup_id = uuid.uuid4()
    a, b = uuid.uuid4(), uuid.uuid4()

    first = deterministic_coin_flip(matchup_id, 0, a, b)
    assert all(deterministic_coin_flip(matchup_id, 0, a, b) == first for _ in range(10))
    assert first in (a, b)

    # Different stable inputs flip both ways eventually.
    outcomes = {deterministic_coin_flip(uuid.uuid4(), i, a, b) for i in range(50)}
    assert outcomes == {a, b}


def test_game_agent_order_alternates_starting_player():
    a, b = uuid.uuid4(), uuid.uuid4()
    assert game_agent_order(a, b, 0) == [a, b]
    assert game_agent_order(a, b, 1) == [b, a]
    assert game_agent_order(a, b, 2) == [a, b]

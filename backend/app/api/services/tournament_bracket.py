"""Pure double-elimination bracket math (no DB access).

Generates the full set of matchups for a tournament — winners bracket,
losers bracket, grand final and the conditional grand-final reset — wired
together through winner/loser source links, plus the per-matchup ``stage``
index that drives round-by-round scheduling (a matchup is only filled once
every matchup with a lower stage is terminal).
"""

import hashlib
import random
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.models.tournament import BracketSide, SlotSourceRole


MIN_ENTRANTS = 2


@dataclass
class SlotSource:
    """A matchup slot fed by the winner or loser of another matchup."""

    matchup_id: UUID
    role: SlotSourceRole


@dataclass
class MatchupSpec:
    """Blueprint for one TournamentMatchup row."""

    bracket: BracketSide
    round: int
    position: int
    stage: int
    id: UUID = field(default_factory=uuid4)
    agent1_id: UUID | None = None
    agent2_id: UUID | None = None
    slot1_source: SlotSource | None = None
    slot2_source: SlotSource | None = None


def next_power_of_two(n: int) -> int:
    return 1 << (n - 1).bit_length()


def generate_double_elimination_bracket(
    agent_ids: list[UUID],
    rng: random.Random,
) -> list[MatchupSpec]:
    """
    Build all matchups for a double-elimination bracket over ``agent_ids``.

    Seeding is random (entrant order and bye placement). Byes are spread over
    distinct first-round matchups, which is always possible because the number
    of byes is below half the bracket size. The grand-final reset matchup is
    included up-front and is cancelled by the engine when the winners-bracket
    champion wins the grand final.
    """
    n = len(agent_ids)
    if n < MIN_ENTRANTS:
        raise ValueError(f"A bracket requires at least {MIN_ENTRANTS} entrants, got {n}")

    bracket_size = next_power_of_two(n)
    rounds = bracket_size.bit_length() - 1  # winners-bracket round count (k)
    half = bracket_size // 2

    entrants = list(agent_ids)
    rng.shuffle(entrants)
    bye_positions = set(rng.sample(range(half), bracket_size - n))

    specs: list[MatchupSpec] = []

    # --- Winners bracket ---
    wb: dict[tuple[int, int], MatchupSpec] = {}
    entrant_iter = iter(entrants)
    for pos in range(half):
        spec = MatchupSpec(
            bracket=BracketSide.WINNERS,
            round=1,
            position=pos,
            stage=0,
            agent1_id=next(entrant_iter),
            agent2_id=None if pos in bye_positions else next(entrant_iter),
        )
        wb[(1, pos)] = spec
        specs.append(spec)

    for r in range(2, rounds + 1):
        for pos in range(bracket_size >> r):
            spec = MatchupSpec(
                bracket=BracketSide.WINNERS,
                round=r,
                position=pos,
                stage=r - 1,
                slot1_source=SlotSource(wb[(r - 1, 2 * pos)].id, SlotSourceRole.WINNER),
                slot2_source=SlotSource(wb[(r - 1, 2 * pos + 1)].id, SlotSourceRole.WINNER),
            )
            wb[(r, pos)] = spec
            specs.append(spec)

    # --- Losers bracket (absent for a 2-entrant bracket) ---
    lb = _losers_bracket_specs(wb, bracket_size, rounds)
    specs.extend(lb.values())

    # --- Grand final (+ conditional bracket reset) ---
    wb_final = wb[(rounds, 0)]
    if rounds >= 2:  # noqa: PLR2004
        lb_champion_source = SlotSource(lb[(2 * (rounds - 1), 0)].id, SlotSourceRole.WINNER)
        gf_stage = 2 * rounds - 1
    else:
        # 2-entrant bracket: the winners final loser is the losers-bracket champion.
        lb_champion_source = SlotSource(wb_final.id, SlotSourceRole.LOSER)
        gf_stage = 1

    grand_final = MatchupSpec(
        bracket=BracketSide.GRAND_FINAL,
        round=1,
        position=0,
        stage=gf_stage,
        slot1_source=SlotSource(wb_final.id, SlotSourceRole.WINNER),
        slot2_source=lb_champion_source,
    )
    specs.append(grand_final)

    specs.append(
        MatchupSpec(
            bracket=BracketSide.GRAND_FINAL_RESET,
            round=1,
            position=0,
            stage=gf_stage + 1,
            slot1_source=SlotSource(grand_final.id, SlotSourceRole.WINNER),
            slot2_source=SlotSource(grand_final.id, SlotSourceRole.LOSER),
        )
    )

    return specs


def _losers_bracket_specs(
    wb: dict[tuple[int, int], MatchupSpec],
    bracket_size: int,
    rounds: int,
) -> dict[tuple[int, int], MatchupSpec]:
    """
    Losers-bracket matchups for a bracket of ``bracket_size`` (2 * (rounds - 1)
    rounds). Round 1 pairs winners-round-1 losers; even ("minor") rounds bring
    in the next winners-round losers; odd ("major") rounds pair survivors.
    """
    lb: dict[tuple[int, int], MatchupSpec] = {}
    for r in range(1, 2 * (rounds - 1) + 1):
        if r == 1:
            size = bracket_size >> 2
            sources = [
                (
                    SlotSource(wb[(1, 2 * pos)].id, SlotSourceRole.LOSER),
                    SlotSource(wb[(1, 2 * pos + 1)].id, SlotSourceRole.LOSER),
                )
                for pos in range(size)
            ]
        elif r % 2 == 0:
            m = r // 2
            size = bracket_size >> (m + 1)
            sources = [
                (
                    SlotSource(lb[(r - 1, pos)].id, SlotSourceRole.WINNER),
                    # Reverse the drop-in order on alternate rounds to delay rematches.
                    SlotSource(wb[(m + 1, size - 1 - pos if m % 2 == 1 else pos)].id, SlotSourceRole.LOSER),
                )
                for pos in range(size)
            ]
        else:
            m = (r - 1) // 2
            size = bracket_size >> (m + 2)
            sources = [
                (
                    SlotSource(lb[(r - 1, 2 * pos)].id, SlotSourceRole.WINNER),
                    SlotSource(lb[(r - 1, 2 * pos + 1)].id, SlotSourceRole.WINNER),
                )
                for pos in range(size)
            ]

        for pos, (slot1, slot2) in enumerate(sources):
            lb[(r, pos)] = MatchupSpec(
                bracket=BracketSide.LOSERS,
                round=r,
                position=pos,
                stage=r,
                slot1_source=slot1,
                slot2_source=slot2,
            )
    return lb


def deterministic_coin_flip(
    matchup_id: UUID,
    game_index: int,
    first_agent_id: UUID,
    second_agent_id: UUID,
) -> UUID:
    """
    Resolve a drawn game to one side via a reproducible pseudo-random choice
    seeded by the matchup id and game index.
    """
    digest = hashlib.sha256(f"{matchup_id}:{game_index}".encode()).digest()
    return first_agent_id if digest[0] % 2 == 0 else second_agent_id


def game_agent_order(agent1_id: UUID, agent2_id: UUID, game_index: int) -> list[UUID]:
    """
    Ordered agent ids for one best-of-3 game; index 0 is the starting player.
    The starting player alternates between games of a matchup.
    """
    return [agent1_id, agent2_id] if game_index % 2 == 0 else [agent2_id, agent1_id]

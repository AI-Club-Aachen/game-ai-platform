"""Tournament feature tests: API authz/validation plus the bracket engine
(round-by-round advancement, BO3, byes, retries/forfeits, isolation)."""

import uuid

import pytest
from sqlmodel import Session, select

from app.api.repositories.agent import AgentRepository
from app.api.repositories.arena import ArenaRepository
from app.api.repositories.job import JobRepository
from app.api.repositories.match import MatchRepository
from app.api.repositories.submission import SubmissionRepository
from app.api.repositories.tournament import TournamentRepository
from app.api.services.match import MatchService
from app.api.services.match_scheduler import MatchSchedulerService
from app.api.services.tournament import TournamentService
from app.api.services.tournament_bracket import deterministic_coin_flip, game_agent_order
from app.core.config import settings
from app.models.agent import Agent
from app.models.arena import Arena
from app.models.game import GameType
from app.models.job import BuildJob, JobStatus
from app.models.match import Match, MatchStatus
from app.models.submission import Submission
from app.models.tournament import (
    BracketSide,
    GameResolution,
    MatchupStatus,
    Tournament,
    TournamentConfig,
    TournamentGame,
    TournamentStatus,
)
from tests.api.test_users import _create_admin_and_token, _create_verified_user_and_token
from tests.utils import random_email, random_lower_string, random_username, strong_password


API_PREFIX = settings.API_V1_PREFIX
SOME_ID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _make_built_agent(db_session: Session, game_type: GameType = GameType.HEX) -> Agent:
    """Agent with a successfully built active submission (tournament-eligible)."""
    user_id = uuid.uuid4()
    arena = _get_or_create_test_arena(db_session, game_type)
    submission = Submission(
        user_id=user_id,
        name=random_lower_string(8),
        game_type=game_type,
        arena_id=arena.id,
        object_path="path/to/zip",
    )
    submission = SubmissionRepository(db_session).save(submission)
    db_session.add(
        BuildJob(
            submission_id=submission.id,
            status=JobStatus.COMPLETED,
            logs="...",
            image_id="sha256:test",
            image_tag=f"agent:{submission.id}",
        )
    )
    db_session.refresh(submission)
    agent = Agent(
        user_id=user_id,
        name=random_lower_string(8),
        game_type=game_type,
        arena_id=arena.id,
        active_submission_id=submission.id,
    )
    return AgentRepository(db_session).save(agent)


def _build_engine(
    db_session: Session,
) -> tuple[TournamentService, MatchService, TournamentRepository, MatchRepository]:
    match_repository = MatchRepository(db_session)
    agent_repository = AgentRepository(db_session)
    job_repository = JobRepository(db_session)
    tournament_repository = TournamentRepository(db_session)
    arena_repository = ArenaRepository(db_session)
    match_service = MatchService(
        match_repository, job_repository, agent_repository, arena_repository
    )
    service = TournamentService(
        tournament_repository,
        match_repository,
        agent_repository,
        match_service,
        arena_repository,
    )
    return service, match_service, tournament_repository, match_repository


def _tournament_matches(
    match_repo: MatchRepository, tournament_id: uuid.UUID, status: str | None = None
) -> list[Match]:
    matches = match_repo.list_matches(0, 500, status=status, with_tournament=True)
    return [m for m in matches if m.tournament_id == tournament_id]


def _matchups_by_key(tournament_repo: TournamentRepository, tournament_id: uuid.UUID) -> dict:
    return {(m.bracket, m.round, m.position): m for m in tournament_repo.list_matchups(tournament_id)}


def _matchup_for_match(db_session: Session, tournament_repo: TournamentRepository, match: Match):
    game = db_session.exec(select(TournamentGame).where(TournamentGame.match_id == match.id)).one()
    return tournament_repo.get_matchup(game.matchup_id)


def _queued_match_for_game(
    db_session: Session, m_repo: MatchRepository, tournament_id: uuid.UUID, game_index: int
) -> Match:
    """The queued Match backing a specific game index (games 0 and 1 are queued in parallel)."""
    for match in _tournament_matches(m_repo, tournament_id, status="queued"):
        game = db_session.exec(select(TournamentGame).where(TournamentGame.match_id == match.id)).one()
        if game.game_index == game_index:
            return match
    raise AssertionError(f"No queued match for game index {game_index}")


async def _start_tournament(
    db_session: Session,
    n_agents: int,
    max_concurrent: int = 8,
) -> tuple[TournamentService, MatchService, TournamentRepository, MatchRepository, Tournament, list[Agent]]:
    agents = [_make_built_agent(db_session) for _ in range(n_agents)]
    service, match_service, t_repo, m_repo = _build_engine(db_session)
    arena = _get_or_create_test_arena(db_session, GameType.HEX)
    config = TournamentConfig(max_concurrent_matches=max_concurrent)
    tournament = service.create_tournament("Test Cup", arena.id, [a.id for a in agents], config)
    tournament = await service.start_tournament(tournament.id)
    return service, match_service, t_repo, m_repo, tournament, agents


async def _complete(match_service: MatchService, match: Match, winner: uuid.UUID | str) -> None:
    await match_service.update_match(str(match.id), status="completed", result={"winner": str(winner)})


async def _drive_to_completion(db_session, service, match_service, t_repo, m_repo, tournament, decide, max_passes=200):
    """Repeatedly complete queued tournament matches per ``decide(match, matchup)`` and advance."""
    for _ in range(max_passes):
        tournament = t_repo.get_by_id(tournament.id)
        terminal = (TournamentStatus.COMPLETED, TournamentStatus.CANCELLED, TournamentStatus.NEEDS_ATTENTION)
        if tournament.status in terminal:
            return tournament
        for match in _tournament_matches(m_repo, tournament.id, status=MatchStatus.QUEUED.value):
            matchup = _matchup_for_match(db_session, t_repo, match)
            await _complete(match_service, match, decide(match, matchup))
        await service.advance_tournament(tournament)
    raise AssertionError("Tournament did not finish within the pass budget")


# ---------------------------------------------------------------------------
# API: authorization
# ---------------------------------------------------------------------------

TOURNAMENT_ROUTES = [
    ("POST", f"{API_PREFIX}/tournaments"),
    ("POST", f"{API_PREFIX}/tournaments/{SOME_ID}/start"),
    ("POST", f"{API_PREFIX}/tournaments/{SOME_ID}/cancel"),
    ("POST", f"{API_PREFIX}/tournaments/{SOME_ID}/matchups/{SOME_ID}/resolve"),
    ("GET", f"{API_PREFIX}/tournaments"),
    ("GET", f"{API_PREFIX}/tournaments/{SOME_ID}"),
    ("GET", f"{API_PREFIX}/tournaments/{SOME_ID}/bracket"),
]


@pytest.mark.anyio
@pytest.mark.parametrize(("method", "path"), TOURNAMENT_ROUTES)
async def test_anonymous_is_denied_on_all_tournament_routes(api_client, method, path):
    response = await api_client.request(method, path)
    assert response.status_code in (401, 403), (
        f"{method} {path} should deny anonymous access, got {response.status_code}"
    )


@pytest.mark.anyio
async def test_verified_user_can_read_but_not_mutate(api_client, fake_email_client, db_session):
    _, token = await _create_verified_user_and_token(
        api_client, fake_email_client, random_username(), random_email(), strong_password()
    )
    headers = {"Authorization": token}

    agents = [_make_built_agent(db_session) for _ in range(2)]
    service, *_ = _build_engine(db_session)
    arena = _get_or_create_test_arena(db_session, GameType.HEX)
    tournament = service.create_tournament("Readable Cup", arena.id, [a.id for a in agents], TournamentConfig())

    for path in (
        f"{API_PREFIX}/tournaments",
        f"{API_PREFIX}/tournaments/{tournament.id}",
        f"{API_PREFIX}/tournaments/{tournament.id}/bracket",
    ):
        response = await api_client.get(path, headers=headers)
        assert response.status_code == 200, f"GET {path} should be readable for a verified user"

    mutations = [
        (
            "POST",
            f"{API_PREFIX}/tournaments",
            {"name": "x", "arena_id": str(arena.id), "agent_ids": [str(a.id) for a in agents]},
        ),
        ("POST", f"{API_PREFIX}/tournaments/{tournament.id}/start", None),
        ("POST", f"{API_PREFIX}/tournaments/{tournament.id}/cancel", None),
        (
            "POST",
            f"{API_PREFIX}/tournaments/{tournament.id}/matchups/{SOME_ID}/resolve",
            {"winner_agent_id": str(agents[0].id)},
        ),
    ]
    for method, path, body in mutations:
        response = await api_client.request(method, path, headers=headers, json=body)
        assert response.status_code == 403, f"{method} {path} should be admin-only, got {response.status_code}"


# ---------------------------------------------------------------------------
# API: lifecycle and validation
# ---------------------------------------------------------------------------


async def _admin_headers(api_client, fake_email_client, db_session) -> dict:
    _, token = await _create_admin_and_token(
        api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
    )
    return {"Authorization": token}


@pytest.mark.anyio
async def test_admin_tournament_lifecycle(api_client, fake_email_client, db_session):
    headers = await _admin_headers(api_client, fake_email_client, db_session)
    agents = [_make_built_agent(db_session) for _ in range(3)]
    arena = _get_or_create_test_arena(db_session, GameType.HEX)

    response = await api_client.post(
        f"{API_PREFIX}/tournaments",
        headers=headers,
        json={"name": "Hex Open", "arena_id": str(arena.id), "agent_ids": [str(a.id) for a in agents]},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["game_type"] == "hex"
    # Per-game defaults are merged into the stored config (mirrors match creation).
    assert body["config"]["state_init_data"]["board_size"] == 11  # standard Hex size
    tournament_id = body["id"]

    response = await api_client.post(f"{API_PREFIX}/tournaments/{tournament_id}/start", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "running"

    # Starting twice is a state conflict.
    response = await api_client.post(f"{API_PREFIX}/tournaments/{tournament_id}/start", headers=headers)
    assert response.status_code == 409

    # Round 1 matches are queued and tagged with the tournament id.
    queued = _tournament_matches(MatchRepository(db_session), uuid.UUID(tournament_id), status="queued")
    assert queued, "starting the tournament should queue round-1 matches"
    assert all(str(m.tournament_id) == tournament_id for m in queued)

    response = await api_client.get(f"{API_PREFIX}/tournaments/{tournament_id}/bracket", headers=headers)
    assert response.status_code == 200
    bracket = response.json()
    assert len(bracket["entrants"]) == 3
    assert len(bracket["standings"]) == 3
    assert all(e["seed"] is not None for e in bracket["entrants"])
    # 3 entrants -> bracket of 4 -> 2*4-1 = 7 matchups including grand-final reset.
    assert len(bracket["matchups"]) == 7

    response = await api_client.post(f"{API_PREFIX}/tournaments/{tournament_id}/cancel", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    # Cancelling again is a state conflict.
    response = await api_client.post(f"{API_PREFIX}/tournaments/{tournament_id}/cancel", headers=headers)
    assert response.status_code == 409


@pytest.mark.anyio
async def test_create_tournament_validations(api_client, fake_email_client, db_session):
    headers = await _admin_headers(api_client, fake_email_client, db_session)
    hex_agent = _make_built_agent(db_session, GameType.HEX)
    other_game_agent = _make_built_agent(db_session, GameType.TICTACTOE)
    arena = _get_or_create_test_arena(db_session, GameType.HEX)
    unbuilt_agent = AgentRepository(db_session).save(
        Agent(user_id=uuid.uuid4(), name=random_lower_string(8), game_type=GameType.HEX, arena_id=arena.id)
    )

    async def create(agent_ids: list[str]) -> int:
        response = await api_client.post(
            f"{API_PREFIX}/tournaments",
            headers=headers,
            json={"name": "Bad Cup", "arena_id": str(arena.id), "agent_ids": agent_ids},
        )
        return response.status_code

    # Fewer than 2 entrants is rejected by the schema.
    assert await create([str(hex_agent.id)]) == 422
    # Duplicates rejected.
    assert await create([str(hex_agent.id), str(hex_agent.id)]) == 400
    # Unknown agent rejected.
    assert await create([str(hex_agent.id), str(uuid.uuid4())]) == 400
    # Wrong game type rejected.
    assert await create([str(hex_agent.id), str(other_game_agent.id)]) == 400
    # Agent without a successful active submission rejected.
    assert await create([str(hex_agent.id), str(unbuilt_agent.id)]) == 400


@pytest.mark.anyio
async def test_resolve_matchup_requires_needs_attention(api_client, fake_email_client, db_session):
    headers = await _admin_headers(api_client, fake_email_client, db_session)
    _, _, t_repo, _, tournament, agents = await _start_tournament(db_session, 2)

    matchup = next(m for m in t_repo.list_matchups(tournament.id) if m.status == MatchupStatus.IN_PROGRESS)

    response = await api_client.post(
        f"{API_PREFIX}/tournaments/{tournament.id}/matchups/{matchup.id}/resolve",
        headers=headers,
        json={"winner_agent_id": str(agents[0].id)},
    )
    assert response.status_code == 409

    response = await api_client.post(
        f"{API_PREFIX}/tournaments/{tournament.id}/matchups/{uuid.uuid4()}/resolve",
        headers=headers,
        json={"winner_agent_id": str(agents[0].id)},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Engine: byes, gating, concurrency
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_bye_matchup_auto_advances(db_session):
    _, _, t_repo, m_repo, tournament, _ = await _start_tournament(db_session, 3)

    matchups = _matchups_by_key(t_repo, tournament.id)
    round_one = [matchups[(BracketSide.WINNERS, 1, 0)], matchups[(BracketSide.WINNERS, 1, 1)]]
    byes = [m for m in round_one if m.agent2_id is None]
    played = [m for m in round_one if m.agent2_id is not None]
    assert len(byes) == 1
    assert len(played) == 1

    # The bye matchup completed immediately without any games; its agent advanced.
    assert byes[0].status == MatchupStatus.COMPLETED
    assert byes[0].winner_agent_id == byes[0].agent1_id
    games = [g for g in t_repo.list_games(tournament.id) if g.matchup_id == byes[0].id]
    assert games == []

    # The real matchup queued both parallel games (G1 and G2) of the BO3.
    assert played[0].status == MatchupStatus.IN_PROGRESS
    assert len(_tournament_matches(m_repo, tournament.id, status="queued")) == 2


@pytest.mark.anyio
async def test_round_by_round_gating_across_brackets(db_session):
    service, match_service, t_repo, m_repo, tournament, _ = await _start_tournament(db_session, 4)

    matchups = _matchups_by_key(t_repo, tournament.id)
    wb1_a = matchups[(BracketSide.WINNERS, 1, 0)]
    wb1_b = matchups[(BracketSide.WINNERS, 1, 1)]

    async def win_twice(matchup) -> None:
        """Let agent1 of the matchup win the BO3 2-0."""
        for _ in range(2):
            match = next(
                m
                for m in _tournament_matches(m_repo, tournament.id, status="queued")
                if _matchup_for_match(db_session, t_repo, m).id == matchup.id
            )
            await _complete(match_service, match, matchup.agent1_id)
            await service.advance_tournament(tournament)

    await win_twice(wb1_a)
    assert t_repo.get_matchup(wb1_a.id).status == MatchupStatus.COMPLETED

    # Stage 1 (winners final + losers round 1) must NOT open while wb1_b is unfinished,
    # even though the winners-final slot fed by wb1_a is already known.
    wb_final = matchups[(BracketSide.WINNERS, 2, 0)]
    lb1 = matchups[(BracketSide.LOSERS, 1, 0)]
    assert t_repo.get_matchup(wb_final.id).status == MatchupStatus.PENDING
    assert t_repo.get_matchup(lb1.id).status == MatchupStatus.PENDING
    queued = _tournament_matches(m_repo, tournament.id, status="queued")
    assert all(_matchup_for_match(db_session, t_repo, m).id == wb1_b.id for m in queued)

    await win_twice(wb1_b)

    # Now the whole round is done: both stage-1 matchups open in parallel.
    assert t_repo.get_matchup(wb_final.id).status == MatchupStatus.IN_PROGRESS
    assert t_repo.get_matchup(lb1.id).status == MatchupStatus.IN_PROGRESS
    queued = _tournament_matches(m_repo, tournament.id, status="queued")
    assert {_matchup_for_match(db_session, t_repo, m).id for m in queued} == {wb_final.id, lb1.id}


@pytest.mark.anyio
async def test_parallel_cap_is_respected(db_session):
    service, match_service, t_repo, m_repo, tournament, _ = await _start_tournament(db_session, 8, max_concurrent=2)

    # 8 entrants -> 4 round-1 matchups ready, but only 2 matches may be active.
    active = _tournament_matches(m_repo, tournament.id, status="queued")
    assert len(active) == 2

    # Completing one frees capacity for the next pending matchup of the same round.
    match = active[0]
    matchup = _matchup_for_match(db_session, t_repo, match)
    await _complete(match_service, match, matchup.agent1_id)
    await service.advance_tournament(tournament)
    assert len(_tournament_matches(m_repo, tournament.id, status="queued")) == 2


# ---------------------------------------------------------------------------
# Engine: best-of-3 mechanics
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_best_of_three_alternates_starting_player(db_session):
    service, match_service, t_repo, m_repo, tournament, _ = await _start_tournament(db_session, 2)
    matchup = next(m for m in t_repo.list_matchups(tournament.id) if m.status == MatchupStatus.IN_PROGRESS)
    a1, a2 = matchup.agent1_id, matchup.agent2_id

    # Games 1 and 2 are queued together (parallelizable) with swapped starters:
    # G1 has agent1 starting, G2 has agent2 starting.
    queued = _tournament_matches(m_repo, tournament.id, status="queued")
    assert len(queued) == 2
    game1 = _queued_match_for_game(db_session, m_repo, tournament.id, 0)
    game2 = _queued_match_for_game(db_session, m_repo, tournament.id, 1)
    assert game1.agent_ids == [str(a1), str(a2)]
    assert game2.agent_ids == [str(a2), str(a1)]
    assert len([g for g in t_repo.list_games(tournament.id) if g.matchup_id == matchup.id]) == 2

    # Split the first two games 1-1 to force a decider.
    await _complete(match_service, game1, a1)
    await _complete(match_service, game2, a2)
    await service.advance_tournament(tournament)

    # 1-1 forces a decider whose starting player is a reproducible coin flip.
    [game3] = _tournament_matches(m_repo, tournament.id, status="queued")
    assert game3.agent_ids == [str(aid) for aid in game_agent_order(matchup.id, a1, a2, 2)]
    assert sorted(game3.agent_ids) == sorted([str(a1), str(a2)])
    await _complete(match_service, game3, a2)
    await service.advance_tournament(tournament)

    refreshed = t_repo.get_matchup(matchup.id)
    assert refreshed.status == MatchupStatus.COMPLETED
    assert refreshed.winner_agent_id == a2
    assert len([g for g in t_repo.list_games(tournament.id) if g.matchup_id == matchup.id]) == 3


@pytest.mark.anyio
async def test_two_nil_sweep_completes_without_a_decider(db_session):
    """When the parallel games are both won by one agent, no decider is created."""
    service, match_service, t_repo, m_repo, tournament, _ = await _start_tournament(db_session, 2)
    matchup = next(m for m in t_repo.list_matchups(tournament.id) if m.status == MatchupStatus.IN_PROGRESS)
    a1 = matchup.agent1_id

    game1 = _queued_match_for_game(db_session, m_repo, tournament.id, 0)
    game2 = _queued_match_for_game(db_session, m_repo, tournament.id, 1)
    await _complete(match_service, game1, a1)
    await _complete(match_service, game2, a1)
    await service.advance_tournament(tournament)

    refreshed = t_repo.get_matchup(matchup.id)
    assert refreshed.status == MatchupStatus.COMPLETED
    assert refreshed.winner_agent_id == a1
    # No game 3: the matchup was decided 2-0.
    assert len([g for g in t_repo.list_games(tournament.id) if g.matchup_id == matchup.id]) == 2


@pytest.mark.anyio
async def test_draw_is_resolved_by_deterministic_coin_flip(db_session):
    service, match_service, t_repo, m_repo, tournament, _ = await _start_tournament(db_session, 2)
    matchup = next(m for m in t_repo.list_matchups(tournament.id) if m.status == MatchupStatus.IN_PROGRESS)

    match = _queued_match_for_game(db_session, m_repo, tournament.id, 0)
    await _complete(match_service, match, "draw")
    await service.advance_tournament(tournament)

    game = db_session.exec(select(TournamentGame).where(TournamentGame.match_id == match.id)).one()
    expected = deterministic_coin_flip(matchup.id, 0, matchup.agent1_id, matchup.agent2_id)
    assert game.resolution == GameResolution.DRAW_COIN_FLIP
    assert game.winner_agent_id == expected


# ---------------------------------------------------------------------------
# Engine: failures
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_client_error_forfeits_the_game(db_session):
    service, match_service, t_repo, m_repo, tournament, _ = await _start_tournament(db_session, 2)
    matchup = next(m for m in t_repo.list_matchups(tournament.id) if m.status == MatchupStatus.IN_PROGRESS)

    # The worker attributes the win to the non-erring agent on client errors.
    match = _queued_match_for_game(db_session, m_repo, tournament.id, 0)
    await match_service.update_match(
        str(match.id), status="client_error", result={"winner": str(matchup.agent2_id), "reason": "Invalid move"}
    )
    await service.advance_tournament(tournament)

    game = db_session.exec(select(TournamentGame).where(TournamentGame.match_id == match.id)).one()
    assert game.resolution == GameResolution.FORFEIT_CLIENT_ERROR
    assert game.winner_agent_id == matchup.agent2_id
    assert game.retry_count == 0  # forfeits are not retried


@pytest.mark.anyio
async def test_unattributable_client_error_needs_attention(db_session):
    service, match_service, t_repo, m_repo, tournament, _ = await _start_tournament(db_session, 2)
    matchup = next(m for m in t_repo.list_matchups(tournament.id) if m.status == MatchupStatus.IN_PROGRESS)

    match = _queued_match_for_game(db_session, m_repo, tournament.id, 0)
    await match_service.update_match(str(match.id), status="client_error", result={"reason": "both crashed"})
    await service.advance_tournament(tournament)

    assert t_repo.get_matchup(matchup.id).status == MatchupStatus.NEEDS_ATTENTION
    assert t_repo.get_by_id(tournament.id).status == TournamentStatus.NEEDS_ATTENTION


@pytest.mark.anyio
async def test_infra_failure_retries_then_needs_attention_then_admin_resolves(db_session, monkeypatch):
    monkeypatch.setattr(settings, "TOURNAMENT_MAX_GAME_RETRIES", 1)
    service, match_service, t_repo, m_repo, tournament, _ = await _start_tournament(db_session, 2)
    matchup = next(m for m in t_repo.list_matchups(tournament.id) if m.status == MatchupStatus.IN_PROGRESS)

    # First infrastructure failure on game 1: it is re-queued with a fresh match.
    match = _queued_match_for_game(db_session, m_repo, tournament.id, 0)
    await match_service.update_match(str(match.id), status="failed")
    await service.advance_tournament(tournament)

    game = db_session.exec(
        select(TournamentGame).where(TournamentGame.matchup_id == matchup.id, TournamentGame.game_index == 0)
    ).one()
    assert game.retry_count == 1
    assert game.match_id is not None
    assert game.match_id != match.id
    assert t_repo.get_matchup(matchup.id).status == MatchupStatus.IN_PROGRESS

    # Second failure exhausts the cap: no auto-decision, admin attention required.
    await match_service.update_match(str(game.match_id), status="failed")
    await service.advance_tournament(tournament)
    db_session.refresh(game)
    assert game.retry_count == 1
    assert t_repo.get_matchup(matchup.id).status == MatchupStatus.NEEDS_ATTENTION
    assert t_repo.get_by_id(tournament.id).status == TournamentStatus.NEEDS_ATTENTION

    # Admin resolves the stuck matchup; the tournament resumes and advances.
    service.resolve_matchup(tournament.id, matchup.id, matchup.agent1_id)
    assert t_repo.get_matchup(matchup.id).status == MatchupStatus.COMPLETED
    tournament = t_repo.get_by_id(tournament.id)
    assert tournament.status == TournamentStatus.RUNNING

    await service.advance_tournament(tournament)
    grand_final = next(m for m in t_repo.list_matchups(tournament.id) if m.bracket == BracketSide.GRAND_FINAL)
    assert grand_final.status == MatchupStatus.IN_PROGRESS
    assert grand_final.agent1_id == matchup.agent1_id


@pytest.mark.anyio
async def test_advancement_is_idempotent(db_session):
    service, match_service, t_repo, m_repo, tournament, _ = await _start_tournament(db_session, 2)

    # Both parallel games are queued at open; resolve only game 1.
    match = _queued_match_for_game(db_session, m_repo, tournament.id, 0)
    matchup = _matchup_for_match(db_session, t_repo, match)
    await _complete(match_service, match, matchup.agent1_id)

    for _ in range(3):
        await service.advance_tournament(tournament)

    games = [g for g in t_repo.list_games(tournament.id) if g.matchup_id == matchup.id]
    # G1 and G2 created once each at open; repeated advances add no duplicates and
    # no decider (G2 is still unresolved, so the matchup is not yet 1-1).
    assert len(games) == 2
    assert sum(1 for g in games if g.winner_agent_id is not None) == 1
    assert len(_tournament_matches(m_repo, tournament.id)) == 2


# ---------------------------------------------------------------------------
# Engine: full runs (progression, grand final, bracket reset, standings)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_full_tournament_winners_champion_no_reset(db_session):
    service, match_service, t_repo, m_repo, tournament, agents = await _start_tournament(db_session, 5)
    strength = {agent.id: i for i, agent in enumerate(agents)}

    def strongest_wins(match: Match, _matchup) -> uuid.UUID:
        ids = [uuid.UUID(a) for a in match.agent_ids]
        return max(ids, key=lambda a: strength[a])

    tournament = await _drive_to_completion(
        db_session, service, match_service, t_repo, m_repo, tournament, strongest_wins
    )

    assert tournament.status == TournamentStatus.COMPLETED
    assert tournament.winner_agent_id == agents[-1].id  # the strongest agent is undefeated

    finals = (BracketSide.GRAND_FINAL, BracketSide.GRAND_FINAL_RESET)
    matchups = {m.bracket: m for m in t_repo.list_matchups(tournament.id) if m.bracket in finals}
    assert matchups[BracketSide.GRAND_FINAL].winner_agent_id == agents[-1].id
    # The winners-bracket champion defended the grand final: no bracket reset.
    assert matchups[BracketSide.GRAND_FINAL_RESET].status == MatchupStatus.CANCELLED

    standings = service.get_bracket(tournament.id)["standings"]
    assert standings[0]["agent_id"] == agents[-1].id
    assert standings[0]["placement"] == 1
    assert standings[1]["placement"] == 2
    # The second strongest agent loses only to the champion and finishes second.
    assert standings[1]["agent_id"] == agents[-2].id
    # Everyone is placed once the tournament completes.
    assert all(s["placement"] is not None for s in standings)


@pytest.mark.anyio
async def test_full_tournament_with_grand_final_bracket_reset(db_session):
    service, match_service, t_repo, m_repo, tournament, agents = await _start_tournament(db_session, 4)
    strength = {agent.id: i for i, agent in enumerate(agents)}

    def upset_in_the_finals(match: Match, matchup) -> uuid.UUID:
        ids = [uuid.UUID(a) for a in match.agent_ids]
        if matchup.bracket in (BracketSide.GRAND_FINAL, BracketSide.GRAND_FINAL_RESET):
            return min(ids, key=lambda a: strength[a])  # losers-bracket champion upsets
        return max(ids, key=lambda a: strength[a])

    tournament = await _drive_to_completion(
        db_session, service, match_service, t_repo, m_repo, tournament, upset_in_the_finals
    )

    assert tournament.status == TournamentStatus.COMPLETED
    grand_final = next(m for m in t_repo.list_matchups(tournament.id) if m.bracket == BracketSide.GRAND_FINAL)
    reset = next(m for m in t_repo.list_matchups(tournament.id) if m.bracket == BracketSide.GRAND_FINAL_RESET)

    # The losers-bracket champion (slot 2) won the grand final, forcing the reset matchup.
    assert grand_final.winner_agent_id == grand_final.agent2_id
    assert reset.status == MatchupStatus.COMPLETED
    assert reset.agent1_id == grand_final.agent2_id
    assert reset.agent2_id == grand_final.agent1_id
    assert tournament.winner_agent_id == reset.winner_agent_id
    assert reset.winner_agent_id == grand_final.agent2_id

    # The winners-bracket champion needed to lose twice; it placed second.
    standings = service.get_bracket(tournament.id)["standings"]
    assert standings[0]["agent_id"] == tournament.winner_agent_id
    assert standings[1]["agent_id"] == grand_final.agent1_id


# ---------------------------------------------------------------------------
# Isolation from the normal match system
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tournament_matches_do_not_touch_agent_stats(db_session):
    _, match_service, t_repo, m_repo, tournament, agents = await _start_tournament(db_session, 2)
    before = {a.id: (a.wins, a.losses, a.draws, a.matches_played, a.elo) for a in agents}

    match = _queued_match_for_game(db_session, m_repo, tournament.id, 0)
    matchup = _matchup_for_match(db_session, t_repo, match)
    await _complete(match_service, match, matchup.agent1_id)

    agent_repo = AgentRepository(db_session)
    for agent in agents:
        refreshed = agent_repo.get_by_id(agent.id)
        assert (refreshed.wins, refreshed.losses, refreshed.draws, refreshed.matches_played, refreshed.elo) == before[
            agent.id
        ], "tournament matches must not update global agent stats or ELO"


@pytest.mark.anyio
async def test_auto_scheduler_ignores_tournament_matches(db_session):
    _, _, _, m_repo, tournament, _ = await _start_tournament(db_session, 2)
    assert _tournament_matches(m_repo, tournament.id, status="queued"), "precondition: a tournament match is queued"

    # Settle normal matches left behind by other tests so only tournament
    # matches remain active in the shared test database.
    for status in (MatchStatus.QUEUED.value, MatchStatus.RUNNING.value):
        for leftover in m_repo.list_matches(0, 500, status=status, with_tournament=False):
            leftover.status = MatchStatus.COMPLETED
            m_repo.save(leftover)

    # The random auto-scheduler's queue gate must not be blocked by tournament matches.
    scheduler = MatchSchedulerService()
    assert scheduler._check_match_queue(m_repo) is True  # noqa: SLF001

    # A normal queued match still closes the gate.
    normal = m_repo.save(Match(game_type=GameType.HEX, status=MatchStatus.QUEUED, config={}, agent_ids=[]))
    assert scheduler._check_match_queue(m_repo) is False  # noqa: SLF001
    normal.status = MatchStatus.COMPLETED
    m_repo.save(normal)

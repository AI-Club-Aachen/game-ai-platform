"""Tests for the paginated /agent_containers list envelope (data/total/status_counts)."""

import uuid

import pytest
from sqlmodel import Session

from app.core.config import settings
from app.models.agent_container import AgentContainer
from tests.api.test_permissions import _admin, _make_agent, _make_match


API_PREFIX = settings.API_V1_PREFIX


def _make_container(db_session: Session, agent_id: str, match_id: str, status: str) -> None:
    container = AgentContainer(
        container_id=f"c-{uuid.uuid4()}",
        agent_id=uuid.UUID(agent_id),
        match_id=uuid.UUID(match_id),
        status=status,
        image="agent:test",
    )
    db_session.add(container)
    db_session.commit()


@pytest.mark.anyio
async def test_container_list_returns_paginated_envelope_with_status_tallies(
    api_client, fake_email_client, db_session
):
    admin_id, headers = await _admin(api_client, fake_email_client, db_session)
    agent = _make_agent(db_session, admin_id)
    # Use fresh match to isolate counts.
    match = _make_match(db_session, [str(agent.id)])
    qs = f"match_id={match.id}"

    # Three running, one exited, one error -> five total for this match.
    for status in ("running", "running", "running", "exited", "error"):
        _make_container(db_session, str(agent.id), str(match.id), status)

    # Full page: total and status_counts cover every matching row.
    resp = await api_client.get(f"{API_PREFIX}/agent_containers?{qs}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"data", "total", "skip", "limit", "status_counts"}
    assert body["total"] == 5
    assert len(body["data"]) == 5
    assert body["status_counts"] == {"running": 3, "exited": 1, "error": 1}

    # Pagination trims `data` but leaves `total`/`status_counts` global.
    paged = await api_client.get(f"{API_PREFIX}/agent_containers?{qs}&limit=2&skip=0", headers=headers)
    assert paged.status_code == 200
    paged_body = paged.json()
    assert len(paged_body["data"]) == 2
    assert paged_body["total"] == 5
    assert paged_body["status_counts"] == {"running": 3, "exited": 1, "error": 1}

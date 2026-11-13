"""
Admin-editable settings: overrides are validated with the Settings rules, stored in
the DB, applied to the live settings immediately, re-applied on startup, and
resettable to the environment/default value. Secrets never leave the backend.
"""

import pytest

from app.api.repositories.platform_setting import PlatformSettingRepository
from app.api.services.runtime_settings import RuntimeSettingsService
from app.core import runtime_settings
from app.core.config import Settings, settings
from app.core.rate_limit import limiter
from app.models.tournament import TournamentConfig
from tests.api.test_users import _create_admin_and_token, _create_member_and_token
from tests.utils import random_email, random_username, strong_password


API_PREFIX = settings.API_V1_PREFIX
URL = f"{API_PREFIX}/platform/settings"

pytestmark = pytest.mark.anyio


async def _admin(api_client, fake_email_client, db_session) -> dict[str, str]:
    _, token = await _create_admin_and_token(
        api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
    )
    return {"Authorization": token}


def _by_name(body: dict) -> dict[str, dict]:
    return {row["name"]: row for row in body["settings"]}


async def test_get_lists_every_setting_with_sources_and_masks_secrets(api_client, fake_email_client, db_session):
    resp = await api_client.get(URL, headers=await _admin(api_client, fake_email_client, db_session))
    assert resp.status_code == 200
    rows = _by_name(resp.json())

    assert set(rows) == set(Settings.model_fields)
    assert rows["JWT_SECRET_KEY"]["secret"] is True
    assert rows["JWT_SECRET_KEY"]["value"] == "***"
    assert rows["WORKER_API_KEY"]["value"] == "***"
    assert rows["RATE_LIMIT_EMAIL_TOKEN"]["secret"] is False
    assert settings.JWT_SECRET_KEY not in resp.text
    assert settings.WORKER_API_KEY not in resp.text

    assert rows["MAX_UPLOAD_BYTES"]["editable"] is True
    assert rows["MAX_UPLOAD_BYTES"]["group"] == "Limits"
    assert rows["MAX_UPLOAD_BYTES"]["type"] == "int"
    assert rows["MAX_UPLOAD_BYTES"]["minimum"] == 0
    assert rows["MATCH_SCHEDULING_STRATEGY"]["type"] == "choice"
    assert rows["MATCH_SCHEDULING_STRATEGY"]["options"] == ["serial", "concurrent"]
    assert rows["DATABASE_POOL_SIZE"]["editable"] is False
    assert rows["MAX_UPLOAD_BYTES"]["source"] in {"environment", "default"}


async def test_update_applies_immediately_and_reset_restores(api_client, fake_email_client, db_session):
    admin = await _admin(api_client, fake_email_client, db_session)
    base = settings.MAX_AGENTS_PER_ARENA

    resp = await api_client.put(URL, json={"values": {"MAX_AGENTS_PER_ARENA": 7}}, headers=admin)
    assert resp.status_code == 200
    row = _by_name(resp.json())["MAX_AGENTS_PER_ARENA"]
    assert row["value"] == 7
    assert row["base_value"] == base
    assert row["source"] == "override"
    assert row["updated_at"] is not None
    assert settings.MAX_AGENTS_PER_ARENA == 7

    resp = await api_client.put(URL, json={"values": {"MAX_AGENTS_PER_ARENA": None}}, headers=admin)
    assert resp.status_code == 200
    assert _by_name(resp.json())["MAX_AGENTS_PER_ARENA"]["source"] != "override"
    assert base == settings.MAX_AGENTS_PER_ARENA


@pytest.mark.parametrize(
    "values",
    [
        {"MAX_UPLOAD_BYTES": -1},
        {"RATE_LIMIT_LOGIN": "not-a-limit"},
        {"MATCH_SCHEDULING_STRATEGY": "sometimes"},
        {"HUMAN_MOVE_TIME_LIMIT_SECONDS": 1},
        {"JWT_SECRET_KEY": "x" * 40},  # not editable at runtime
        {"NOT_A_SETTING": 1},
    ],
)
async def test_invalid_updates_change_nothing(api_client, fake_email_client, db_session, values):
    admin = await _admin(api_client, fake_email_client, db_session)
    before = settings.model_dump()
    resp = await api_client.put(URL, json={"values": {"MAX_AGENTS_PER_ARENA": 9, **values}}, headers=admin)
    assert resp.status_code == 422
    name = next(iter(values))
    assert any(name in err["msg"] for err in resp.json()["detail"])
    # All-or-nothing: the valid value in the same request was not applied either.
    assert settings.model_dump() == before
    assert PlatformSettingRepository(db_session).list_all() == []


async def test_non_admins_cannot_read_or_change_settings(api_client, fake_email_client, db_session):
    _, token = await _create_member_and_token(
        api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
    )
    member = {"Authorization": token}
    assert (await api_client.get(URL, headers=member)).status_code == 403
    assert (await api_client.put(URL, json={"values": {"MAX_AGENTS_PER_ARENA": 1}}, headers=member)).status_code == 403


async def test_overrides_are_reapplied_on_startup_and_bad_rows_skipped(db_session):
    repository = PlatformSettingRepository(db_session)
    repository.save({"MAX_TOURNAMENT_ENTRANTS": 16, "MAX_HEX_BOARD_SIZE": 1, "REMOVED_SETTING": True})
    runtime_settings.apply_overrides({})  # what a fresh process starts with

    loaded = RuntimeSettingsService(repository).load()

    assert loaded == {"MAX_TOURNAMENT_ENTRANTS": 16}
    assert settings.MAX_TOURNAMENT_ENTRANTS == 16
    assert settings.MAX_HEX_BOARD_SIZE >= 2


async def test_scheduler_switch_applies_immediately(api_client, fake_email_client, db_session):
    admin = await _admin(api_client, fake_email_client, db_session)
    resp = await api_client.put(URL, json={"values": {"MATCH_SCHEDULER_ENABLED": True}}, headers=admin)
    assert resp.status_code == 200
    assert settings.MATCH_SCHEDULER_ENABLED is True
    assert _by_name(resp.json())["MATCH_SCHEDULER_ENABLED"]["source"] == "override"


async def test_editable_settings_have_labels(api_client, fake_email_client, db_session):
    rows = _by_name((await api_client.get(URL, headers=await _admin(api_client, fake_email_client, db_session))).json())
    assert all(row["label"] for row in rows.values() if row["editable"])
    assert rows["JWT_SECRET_KEY"]["label"] is None
    selection = rows["MATCH_SCHEDULER_SELECTION"]
    assert set(selection["option_labels"]) == set(selection["options"])
    assert rows["MATCH_SCHEDULER_INTERVAL_SECONDS"]["option_labels"] is None


async def test_warns_when_concurrency_exceeds_runners(api_client, fake_email_client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "MATCH_RUNNER_REPLICAS", 2)
    admin = await _admin(api_client, fake_email_client, db_session)
    resp = await api_client.put(
        URL,
        json={"values": {"MATCH_SCHEDULING_STRATEGY": "concurrent", "MATCH_MAX_CONCURRENT_MATCHES": 5}},
        headers=admin,
    )
    assert resp.status_code == 200
    assert any("MATCH_MAX_CONCURRENT_MATCHES" in w for w in resp.json()["warnings"])


async def test_tournament_defaults_follow_settings(api_client, fake_email_client, db_session):
    admin = await _admin(api_client, fake_email_client, db_session)
    await api_client.put(
        URL,
        json={"values": {"TOURNAMENT_DEFAULT_TURN_TIME_LIMIT_SECONDS": 3, "TOURNAMENT_MAX_CONCURRENT_MATCHES": 2}},
        headers=admin,
    )
    config = TournamentConfig()
    assert config.turn_time_limit == 3
    assert config.max_concurrent_matches == 2


def test_match_concurrency_defaults_to_runner_count():
    required = {"DATABASE_URL": "postgresql://u:p@localhost/db", "JWT_SECRET_KEY": "x" * 32}
    assert Settings(_env_file=None, **required, MATCH_RUNNER_REPLICAS=3).MATCH_MAX_CONCURRENT_MATCHES == 3
    explicit = Settings(_env_file=None, **required, MATCH_RUNNER_REPLICAS=3, MATCH_MAX_CONCURRENT_MATCHES=5)
    assert explicit.MATCH_MAX_CONCURRENT_MATCHES == 5


def test_url_passwords_are_masked():
    masked = runtime_settings.display_value("DATABASE_URL", "postgresql://user:hunter2@db:5432/app")
    assert masked == "postgresql://user:***@db:5432/app"
    assert runtime_settings.display_value("REDIS_URL", "redis://:hunter2@redis:6379/0") == "redis://:***@redis:6379/0"


async def test_invalid_stored_row_does_not_block_saving(api_client, fake_email_client, db_session):
    repository = PlatformSettingRepository(db_session)
    repository.save({"MAX_HEX_BOARD_SIZE": 1})
    RuntimeSettingsService(repository).load()  # skipped: below the minimum
    admin = await _admin(api_client, fake_email_client, db_session)

    rows = _by_name((await api_client.get(URL, headers=admin)).json())
    assert rows["MAX_HEX_BOARD_SIZE"]["source"] != "override"

    resp = await api_client.put(URL, json={"values": {"MAX_AGENTS_PER_ARENA": 4}}, headers=admin)
    assert resp.status_code == 200
    db_session.expire_all()
    assert {row.name for row in repository.list_all()} == {"MAX_AGENTS_PER_ARENA"}


def test_derived_concurrency_is_not_reported_as_set():
    required = {"DATABASE_URL": "postgresql://u:p@localhost/db", "JWT_SECRET_KEY": "x" * 32}
    derived = Settings(_env_file=None, **required, MATCH_RUNNER_REPLICAS=3)
    assert "MATCH_MAX_CONCURRENT_MATCHES" not in derived.model_fields_set


async def test_setting_the_base_value_removes_the_override(api_client, fake_email_client, db_session):
    """Switching something on and off again must not leave an override that hides later env changes."""
    admin = await _admin(api_client, fake_email_client, db_session)
    base = settings.MATCH_SCHEDULER_ENABLED
    await api_client.put(URL, json={"values": {"MATCH_SCHEDULER_ENABLED": not base}}, headers=admin)
    resp = await api_client.put(URL, json={"values": {"MATCH_SCHEDULER_ENABLED": base}}, headers=admin)

    assert resp.status_code == 200
    assert _by_name(resp.json())["MATCH_SCHEDULER_ENABLED"]["source"] != "override"
    assert runtime_settings.active_overrides() == {}
    db_session.expire_all()
    assert PlatformSettingRepository(db_session).list_all() == []


async def test_rate_limit_change_applies_to_the_next_request(api_client, fake_email_client, db_session):
    admin = await _admin(api_client, fake_email_client, db_session)
    resp = await api_client.put(URL, json={"values": {"RATE_LIMIT_LOGIN": "2/minute"}}, headers=admin)
    assert resp.status_code == 200

    limiter.reset()
    limiter.enabled = True
    try:
        body = {"email": "nobody@example.com", "password": "wrong-password-123"}
        statuses = [(await api_client.post(f"{API_PREFIX}/auth/login", json=body)).status_code for _ in range(3)]
    finally:
        limiter.enabled = False
        limiter.reset()
    assert 429 not in statuses[:2]
    assert statuses[2] == 429

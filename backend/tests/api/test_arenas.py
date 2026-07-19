import pytest

from app.core.config import settings
from app.models.game import GameType
from app.models.user import UserRole
from tests.api.test_users import _create_verified_user_and_token, _set_user_role
from tests.utils import random_email, random_username, strong_password


API_PREFIX = settings.API_V1_PREFIX


async def _create_admin_and_token(
    api_client, fake_email_client, db_session, username: str, email: str, password: str
) -> tuple[str, str]:
    user_id, bearer_token = await _create_verified_user_and_token(
        api_client, fake_email_client, username, email, password
    )
    _set_user_role(db_session, user_id, UserRole.ADMIN)
    return user_id, bearer_token


@pytest.mark.anyio
async def test_arena_packages_validation(api_client, fake_email_client, db_session):
    # Create an admin user to make arena modification requests
    _, bearer_token = await _create_admin_and_token(
        api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
    )
    headers = {"Authorization": bearer_token}

    # 1. Test create arena with packages="numpy" (success)
    response = await api_client.post(
        f"{API_PREFIX}/arenas",
        headers=headers,
        json={
            "name": "Numpy Arena",
            "game_type": GameType.CHESS.value,
            "packages": "numpy",
        },
    )
    assert response.status_code == 201
    arena = response.json()
    assert arena["packages"] == "numpy"
    arena_id = arena["id"]

    # 2. Test default packages value is "numpy"
    response_default = await api_client.post(
        f"{API_PREFIX}/arenas",
        headers=headers,
        json={
            "name": "Default Arena",
            "game_type": GameType.TICTACTOE.value,
        },
    )
    assert response_default.status_code == 201
    assert response_default.json()["packages"] == "numpy"

    # 3. Test create arena with packages="torch" (success)
    response_torch = await api_client.post(
        f"{API_PREFIX}/arenas",
        headers=headers,
        json={
            "name": "Torch Arena",
            "game_type": GameType.HEX.value,
            "packages": "torch",
        },
    )
    assert response_torch.status_code == 201
    assert response_torch.json()["packages"] == "torch"

    # 4. Test create arena with packages="invalid" (fail with 422)
    response_invalid = await api_client.post(
        f"{API_PREFIX}/arenas",
        headers=headers,
        json={
            "name": "Invalid Arena",
            "game_type": GameType.CHESS.value,
            "packages": "invalid",
        },
    )
    assert response_invalid.status_code == 422

    # 5. Test update arena's packages to "torch" (success)
    response_update = await api_client.put(
        f"{API_PREFIX}/arenas/{arena_id}",
        headers=headers,
        json={"packages": "torch"},
    )
    assert response_update.status_code == 200
    assert response_update.json()["packages"] == "torch"

    # 6. Test update arena's packages to "invalid" (fail with 422)
    response_update_invalid = await api_client.put(
        f"{API_PREFIX}/arenas/{arena_id}",
        headers=headers,
        json={"packages": "invalid"},
    )
    assert response_update_invalid.status_code == 422


@pytest.mark.anyio
async def test_worker_can_read_arenas(api_client, fake_email_client, db_session):
    _, bearer_token = await _create_admin_and_token(
        api_client, fake_email_client, db_session, random_username(), random_email(), strong_password()
    )
    admin_headers = {"Authorization": bearer_token}

    # Create arena as admin
    res = await api_client.post(
        f"{API_PREFIX}/arenas",
        headers=admin_headers,
        json={
            "name": "Worker Accessible Arena",
            "game_type": GameType.HEX.value,
            "packages": "torch",
        },
    )
    assert res.status_code == 201
    arena_id = res.json()["id"]

    # Worker accesses GET /arenas/{arena_id} with x-api-key
    worker_headers = {"x-api-key": settings.WORKER_API_KEY}
    get_res = await api_client.get(
        f"{API_PREFIX}/arenas/{arena_id}",
        headers=worker_headers,
    )
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Worker Accessible Arena"
    assert get_res.json()["packages"] == "torch"

    # Worker accesses GET /arenas list with x-api-key
    list_res = await api_client.get(
        f"{API_PREFIX}/arenas",
        headers=worker_headers,
    )
    assert list_res.status_code == 200
    assert any(a["id"] == arena_id for a in list_res.json())


import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

ME = "/api/v1/me"
PROFILE = "/api/v1/me/profile"


async def test_me_returns_email_and_null_profile_initially(client: AsyncClient) -> None:
    response = await client.get(ME)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "dev@example.com"
    assert body["profile"] is None


async def test_me_embeds_profile_once_set(client: AsyncClient) -> None:
    await client.put(PROFILE, json={"display_name": "Bri", "date_of_birth": "1995-03-10"})

    body = (await client.get(ME)).json()
    assert body["profile"]["display_name"] == "Bri"
    assert body["profile"]["age"] is not None


async def test_profile_missing_returns_404(client: AsyncClient) -> None:
    response = await client.get(PROFILE)
    assert response.status_code == 404


async def test_profile_upsert_is_idempotent_and_computes_age(client: AsyncClient) -> None:
    first = await client.put(
        PROFILE, json={"display_name": "Bri", "date_of_birth": "1995-03-10", "sex": "male"}
    )
    assert first.status_code == 200
    assert first.json()["age"] is not None

    second = await client.put(
        PROFILE, json={"display_name": "Bri R", "date_of_birth": "1995-03-10", "sex": "male"}
    )
    assert second.status_code == 200
    assert second.json()["display_name"] == "Bri R"

    fetched = await client.get(PROFILE)
    assert fetched.json()["display_name"] == "Bri R"


async def test_future_date_of_birth_is_rejected(client: AsyncClient) -> None:
    response = await client.put(PROFILE, json={"date_of_birth": "2999-01-01"})
    assert response.status_code == 422

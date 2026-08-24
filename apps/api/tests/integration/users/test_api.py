import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

ME = "/api/v1/me"


async def test_me_returns_the_account_email(client: AsyncClient) -> None:
    response = await client.get(ME)
    assert response.status_code == 200
    assert response.json()["email"] == "dev@example.com"

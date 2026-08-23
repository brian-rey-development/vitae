import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_meta(client: AsyncClient) -> None:
    response = await client.get("/api/v1/meta")
    assert response.status_code == 200
    assert response.json()["app_name"] == "Vitae"

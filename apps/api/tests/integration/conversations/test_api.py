import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

BASE = "/api/v1/conversations"


async def test_create_and_list(client: AsyncClient) -> None:
    created = await client.post(BASE, json={"title": "t"})
    assert created.status_code == 200
    body = created.json()
    assert "user_id" not in body

    listed = await client.get(BASE)
    assert [c["id"] for c in listed.json()] == [body["id"]]


async def test_get_one_conversation(client: AsyncClient) -> None:
    conversation_id = (await client.post(BASE, json={"title": "t"})).json()["id"]

    fetched = await client.get(f"{BASE}/{conversation_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == conversation_id


async def test_unknown_conversation_returns_404(client: AsyncClient) -> None:
    missing = "00000000-0000-0000-0000-0000000000ff"

    response = await client.get(f"{BASE}/{missing}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"

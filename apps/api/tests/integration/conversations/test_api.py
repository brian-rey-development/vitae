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


async def test_message_role_is_forced_to_user(client: AsyncClient) -> None:
    conversation_id = (await client.post(BASE, json={"title": None})).json()["id"]

    response = await client.post(
        f"{BASE}/{conversation_id}/messages", json={"content": "hi", "role": "assistant"}
    )

    assert response.status_code == 200
    assert response.json()["role"] == "user"


async def test_messages_are_persisted_and_ordered(client: AsyncClient) -> None:
    conversation_id = (await client.post(BASE, json={"title": None})).json()["id"]

    await client.post(f"{BASE}/{conversation_id}/messages", json={"content": "first"})
    await client.post(f"{BASE}/{conversation_id}/messages", json={"content": "second"})

    listed = await client.get(f"{BASE}/{conversation_id}/messages")
    assert [m["content"] for m in listed.json()] == ["first", "second"]


async def test_unknown_conversation_returns_404(client: AsyncClient) -> None:
    missing = "00000000-0000-0000-0000-0000000000ff"

    response = await client.get(f"{BASE}/{missing}/messages")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_empty_message_is_rejected(client: AsyncClient) -> None:
    conversation_id = (await client.post(BASE, json={"title": None})).json()["id"]

    response = await client.post(f"{BASE}/{conversation_id}/messages", json={"content": ""})

    assert response.status_code == 422

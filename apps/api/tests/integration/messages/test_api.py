import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

CONVERSATIONS = "/api/v1/conversations"


async def _new_conversation(client: AsyncClient) -> str:
    return (await client.post(CONVERSATIONS, json={"title": None})).json()["id"]


async def test_message_role_is_forced_to_user(client: AsyncClient) -> None:
    conversation_id = await _new_conversation(client)

    response = await client.post(
        f"{CONVERSATIONS}/{conversation_id}/messages",
        json={"content": "hi", "role": "assistant"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "user"


async def test_messages_are_persisted_and_ordered(client: AsyncClient) -> None:
    conversation_id = await _new_conversation(client)

    await client.post(f"{CONVERSATIONS}/{conversation_id}/messages", json={"content": "first"})
    await client.post(f"{CONVERSATIONS}/{conversation_id}/messages", json={"content": "second"})

    listed = await client.get(f"{CONVERSATIONS}/{conversation_id}/messages")
    assert [m["content"] for m in listed.json()] == ["first", "second"]


async def test_messages_on_unknown_conversation_return_404(client: AsyncClient) -> None:
    missing = "00000000-0000-0000-0000-0000000000ff"

    response = await client.get(f"{CONVERSATIONS}/{missing}/messages")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_empty_message_is_rejected(client: AsyncClient) -> None:
    conversation_id = await _new_conversation(client)

    response = await client.post(
        f"{CONVERSATIONS}/{conversation_id}/messages", json={"content": ""}
    )

    assert response.status_code == 422

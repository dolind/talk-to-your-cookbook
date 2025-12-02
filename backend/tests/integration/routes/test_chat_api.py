from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from app.core.config import TargetConfig, get_settings
from app.main import app as fastapi_app

# --- Helpers / fakes ------------------------------------------------------
settings = get_settings()


class FakeAIMessageChunk:
    """Minimal stand-in for LangChain AIMessageChunk"""

    def __init__(self, content: str):
        self.content = content


class FakeRetriever:
    def as_retriever(self, user_id):
        return self


class FakeEmbeddingStore:
    def as_retriever(self, user_id):
        return FakeRetriever()


# --- Autouse fixture for embedding setup ---------------------------------


@pytest.fixture(autouse=True)
def mock_embeddings(monkeypatch):
    """
    Provide fake embedding_stores + patch settings.target_config_list
    so that /stream endpoint can run without real vector DB.
    """
    from app.main import app as fastapi_app

    # attach fake store to app.state
    fastapi_app.state.embedding_stores = {"default:1": FakeEmbeddingStore()}

    # patch settings.target_config_list property
    fake_config = {"default": TargetConfig(target="default", active_version="1", staged_version="1")}
    monkeypatch.setattr(
        settings.__class__,
        "target_config_list",
        property(lambda self: fake_config),
    )
    monkeypatch.setattr(settings, "EMB_RAG_ACTIVE", "default")
    yield


@pytest.mark.asyncio
async def test_list_sessions(authed_client_session: AsyncClient):
    async def fake_astream_events(inputs, config=None, version=None):
        async def generator():
            yield {"event": "on_chat_model_stream", "data": {"chunk": FakeAIMessageChunk("Placeholder")}}

        return generator()

    fake_graph = SimpleNamespace(astream_events=fake_astream_events)
    fastapi_app.state.recipe_assistant_graph = fake_graph
    authed_client_session._transport.app.state.recipe_assistant_graph = fake_graph

    # Create two sessions
    await authed_client_session.post("/api/v1/chat/sessions", json={"title": "Chat A"})
    await authed_client_session.post("/api/v1/chat/sessions", json={"title": "Chat B"})

    res = await authed_client_session.get("/api/v1/chat/sessions")
    assert res.status_code == 200
    payload = res.json()
    assert payload["total"] >= 2
    assert isinstance(payload["items"], list)


@pytest.mark.asyncio
async def test_delete_session(authed_client_session: AsyncClient):
    async def fake_astream_events(inputs, config=None, version=None):
        async def generator():
            yield {"event": "on_chat_model_stream", "data": {"chunk": FakeAIMessageChunk("Bye")}}

        return generator()

    fake_graph = SimpleNamespace(astream_events=fake_astream_events)
    fastapi_app.state.recipe_assistant_graph = fake_graph

    # Create session
    res = await authed_client_session.post("/api/v1/chat/sessions", json={"title": "Chat to delete"})
    assert res.status_code == 200
    session_id = res.json()["id"]

    # Delete it
    res = await authed_client_session.delete(f"/api/v1/chat/sessions/{session_id}")
    assert res.status_code == 204

    # Should now 404 when fetching
    res = await authed_client_session.get(f"/api/v1/chat/sessions/{session_id}/messages")
    assert res.status_code == 404

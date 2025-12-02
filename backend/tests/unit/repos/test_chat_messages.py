import pytest
from unit.repos.fakes import FakeResult, FakeSession

from app.models.chat import ChatMessage, MessageRole
from app.repos import chat_messages

# -------------------------------------------------------------------
# Fakes
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Tests for create_message()
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_message_unit():
    db = FakeSession()

    msg = await chat_messages.create_message(
        db=db,
        session_id="s1",
        content="hello",
        role=MessageRole.user,
    )

    # Message instance created and added
    assert isinstance(msg, ChatMessage)
    assert msg.session_id == "s1"
    assert msg.content == "hello"
    assert msg.role == MessageRole.user

    # DB operations occurred
    assert db.added == [msg]
    assert db.committed == 1
    assert db.refreshed == [msg]


# -------------------------------------------------------------------
# Tests for get_messages()
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_messages_returns_all_unit():
    db = FakeSession()

    # Fake rows returned
    m1 = ChatMessage(session_id="s1", content="a", role=MessageRole.user)
    m2 = ChatMessage(session_id="s1", content="b", role=MessageRole.assistant)

    stmt = object()

    # Proper FakeResult construction
    db.execute_map[stmt] = FakeResult(scalars=[m1, m2])

    # Fake executor
    async def fake_execute(_):
        return db.execute_map[stmt]

    db.execute = fake_execute

    out = await chat_messages.get_messages(db, session_id="s1")
    assert out == [m1, m2]


@pytest.mark.asyncio
async def test_get_messages_empty_unit():
    db = FakeSession()

    stmt = object()
    db.execute_map[stmt] = FakeResult(scalars=[])

    async def fake_execute(_):
        return db.execute_map[stmt]

    db.execute = fake_execute

    out = await chat_messages.get_messages(db, session_id="x")
    assert out == []

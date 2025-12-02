from uuid import uuid4

import pytest

from app.models.chat import ChatSession
from app.repos import chat_sessions


@pytest.mark.asyncio
async def test_create_and_get_session(db_session, test_user):
    custom_thread_id = "thread-xyz"
    session = await chat_sessions.create_session(
        db_session, test_user.id, thread_id=custom_thread_id, title="My Session"
    )

    assert isinstance(session, ChatSession)
    assert session.user_id == test_user.id
    assert session.title == "My Session"

    # Retrieve by ID
    retrieved = await chat_sessions.get_session(db_session, session.id)
    assert retrieved is not None
    assert retrieved.id == session.id
    assert retrieved.user_id == test_user.id


@pytest.mark.asyncio
async def test_get_user_sessions_with_pagination(db_session):
    user_id = "user123"
    other_user_id = "other456"

    # Create sessions for two users
    for i in range(3):
        await chat_sessions.create_session(db_session, user_id, thread_id=str(uuid4()), title=f"user123 chat {i}")
    await chat_sessions.create_session(db_session, other_user_id, thread_id=str(uuid4()), title="other user chat")

    # Default fetch
    sessions, total = await chat_sessions.get_user_sessions(db_session, user_id)
    assert total == 3
    assert len(sessions) == 3
    assert all(s.user_id == user_id for s in sessions)

    # Pagination: skip first 2
    sessions, total = await chat_sessions.get_user_sessions(db_session, user_id, skip=2, limit=5)
    assert total == 3
    assert len(sessions) == 1


@pytest.mark.asyncio
async def test_get_user_sessions_empty(db_session):
    sessions, total = await chat_sessions.get_user_sessions(db_session, "no-such-user")
    assert sessions == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_session_not_found(db_session):
    session = await chat_sessions.get_session(db_session, "nonexistent-id")
    assert session is None


@pytest.mark.asyncio
async def test_delete_session(db_session):
    user_id = "delete-test"
    session = await chat_sessions.create_session(db_session, user_id, thread_id=str(uuid4()), title="to be deleted")

    session_id = session.id
    await chat_sessions.delete_session(db_session, session)

    deleted = await chat_sessions.get_session(db_session, session_id)
    assert deleted is None


@pytest.mark.asyncio
async def test_delete_session_safe_on_none(db_session):
    # Should not raise
    await chat_sessions.delete_session(db_session, None)

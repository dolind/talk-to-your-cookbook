import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.repos import chat_messages


@pytest.mark.asyncio
async def test_create_message_commits_and_refreshes(db_session: AsyncSession):
    session = ChatSession(user_id="u1", title="Session", thread_id="thread-empty")
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    message = await chat_messages.create_message(
        db_session, session_id=session.id, content="Test commit", role=MessageRole.user
    )

    # Should be persisted in DB
    queried = await db_session.get(ChatMessage, message.id)
    assert queried is not None
    assert queried.content == "Test commit"


@pytest.mark.asyncio
async def test_get_messages_empty_for_session(db_session: AsyncSession):
    # Create a chat session with no messages
    session = ChatSession(user_id="u2", title="Empty Session", thread_id="thread-empty")
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    messages = await chat_messages.get_messages(db_session, session_id=session.id)
    assert messages == []  # Should return empty list, not None


@pytest.mark.asyncio
async def test_get_messages_ordered_by_created_at(db_session: AsyncSession):
    session = ChatSession(user_id="u3", title="Ordered Session", thread_id="thread-empty")
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # Create messages out of order
    await chat_messages.create_message(db_session, session.id, "first", MessageRole.user)
    await chat_messages.create_message(db_session, session.id, "second", MessageRole.assistant)
    await chat_messages.create_message(db_session, session.id, "third", MessageRole.user)

    messages = await chat_messages.get_messages(db_session, session.id)
    contents = [m.content for m in messages]
    assert contents == ["first", "second", "third"]  # Must be ordered ASC


@pytest.mark.asyncio
async def test_create_message_with_metadata(db_session: AsyncSession):
    session = ChatSession(user_id="u4", title="Meta Session", thread_id="thread-empty")
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    msg = ChatMessage(
        session_id=session.id, content="Meta message", role=MessageRole.user, meta_data='{"info":"extra"}'
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)

    assert msg.meta_data == '{"info":"extra"}'

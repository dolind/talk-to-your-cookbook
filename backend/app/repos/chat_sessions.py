from typing import Any, Sequence

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.chat import ChatSession


async def create_session(db: AsyncSession, user_id: str, thread_id: str, title: str | None = None) -> ChatSession:
    session = ChatSession(user_id=user_id, title=title, thread_id=thread_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_user_sessions(
    db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100
) -> tuple[Sequence[ChatSession], int | None | Any]:
    query = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc())
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all(), total or 0


async def get_session(db: AsyncSession, session_id: str, owner_id: str | None = None) -> ChatSession | None:
    stmt = select(ChatSession).where(ChatSession.id == session_id)
    if owner_id is not None:
        stmt = stmt.where(ChatSession.user_id == owner_id)
    result = await db.execute(stmt.options(selectinload(ChatSession.messages)))

    return result.scalars().first()


async def delete_session(db: AsyncSession, session: ChatSession):
    if not session:
        return
    await db.delete(session)
    await db.commit()

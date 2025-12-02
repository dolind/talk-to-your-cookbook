from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.chat import ChatMessage, MessageRole


async def create_message(db: AsyncSession, session_id: str, content: str, role: MessageRole) -> ChatMessage:
    message = ChatMessage(session_id=session_id, content=content, role=role)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_messages(db: AsyncSession, session_id: str):
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
    )
    return result.scalars().all()

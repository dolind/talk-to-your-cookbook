import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import AIMessageChunk, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import get_settings
from app.core.deps import get_current_user, get_recipe_repo
from app.database.init_db import get_db
from app.models.chat import MessageRole
from app.models.user import User
from app.repos import chat_messages, chat_sessions
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from app.workflows.recipeassistant.wiring import (
    build_graph_config,
)

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_in: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # assume the default chat is the recipe chat
    ns = session_in.namespace or "recipe-assistant"

    # thread_id encodes namespace + user + UUID
    thread_id = f"{ns}:{current_user.id}:{uuid.uuid4()}"

    session = await chat_sessions.create_session(
        db=db,
        user_id=current_user.id,
        thread_id=thread_id,
        title=session_in.title,
    )
    return session


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    sessions, total = await chat_sessions.get_user_sessions(db, current_user.id, skip, limit)
    return {"items": sessions, "total": total, "skip": skip, "limit": limit}


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await chat_sessions.get_session(db, session_id, current_user.id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return await chat_messages.get_messages(db, session_id)


"""Delete a session. Only deletes app schema table, not checkpoints"""


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await chat_sessions.get_session(db, session_id, current_user.id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # we do not delete checkpoints here, just the app schema
    await chat_sessions.delete_session(db, session)

    return None


@router.post("/sessions/{session_id}/stream")
async def stream_reply(
    session_id: str,
    message_in: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    recipe_repo=Depends(get_recipe_repo),
    request: Request = None,
):
    logger.info(f"Streaming reply for session {session_id}")
    session = ChatSessionResponse.model_validate(await chat_sessions.get_session(db, session_id, current_user.id))

    # 1) Save user message
    await chat_messages.create_message(db, session_id, message_in.content, MessageRole.user)

    # 2) Build the retriever, graph config, graph itself

    store_registry = request.app.state.embedding_stores
    active_embedding_target = settings.target_config_list[settings.EMB_RAG_ACTIVE]
    logger.info(f"Using active embedding target: {active_embedding_target}")
    key = f"{active_embedding_target.target}:{active_embedding_target.active_version}"
    embedding_store = store_registry[key]
    retriever = embedding_store.as_retriever(user_id=current_user.id)
    app_graph = request.app.state.recipe_assistant_graph

    config = await build_graph_config(
        thread_id=session.thread_id,
        user_id=current_user.id,
        recipe_repo=recipe_repo,
        rag_retriever=retriever,
    )

    async def token_stream():
        inputs = {
            "messages": [HumanMessage(content=message_in.content)],
            "selected_recipe_id": message_in.recipe_id or getattr(session, "selected_recipe_id", None),
            "user_id": str(current_user.id),
        }
        chunks: list[AIMessageChunk] = []
        buffered = ""
        try:
            async for ev in app_graph.astream_events(inputs, config=config, version="v2"):
                if ev.get("event") == "on_chat_model_stream":
                    chunk = ev.get("data", {}).get("chunk")
                    if isinstance(chunk, AIMessageChunk) and chunk.content:
                        buffered += chunk.content
                        chunks.append(chunk)
                        # flush only at word boundaries
                        while " " in buffered or "\n" in buffered:
                            space_idx = min(
                                [i for i in (buffered.find(" "), buffered.find("\n")) if i != -1],
                                default=-1,
                            )
                            if space_idx == -1:
                                break
                            token, buffered = buffered[: space_idx + 1], buffered[space_idx + 1 :]
                            yield f"data: {token}\n\n"
        finally:
            # persist assistant message after stream ends
            if chunks:
                logger.info("Final chunks")
                final_msg = "".join(c.content for c in chunks if c.content)
                if final_msg:
                    logger.info(final_msg)
                    await chat_messages.create_message(db, session_id, final_msg, MessageRole.assistant)

            yield "data: [DONE]\n\n"

    from starlette.responses import StreamingResponse

    return StreamingResponse(token_stream(), media_type="text/event-stream")

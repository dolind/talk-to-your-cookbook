from datetime import datetime
from enum import Enum
from typing import Annotated, List, Literal, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ChatSessionBase(BaseModel):
    title: Optional[str] = None
    namespace: Optional[str] = None


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatMessageBase(BaseModel):
    content: str


class ChatMessageCreate(ChatMessageBase):
    recipe_id: Optional[str] = None


class ChatMessageResponse(ChatMessageBase):
    id: str
    session_id: str
    role: MessageRole
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatSessionResponse(ChatSessionBase):
    id: str
    thread_id: str
    created_at: datetime
    messages: List[ChatMessageResponse] = []
    model_config = {"from_attributes": True}


class ChatSessionListResponse(BaseModel):
    items: List[ChatSessionResponse]
    total: int
    skip: int
    limit: int


Role = Literal["user", "assistant", "system"]


class Msg(TypedDict):
    id: str
    role: Role
    content: str
    ts: float


class ChatState(BaseModel):
    # Model-visible chat history
    messages: Annotated[List[BaseMessage], add_messages]
    # Selected recipe context (set by your UI or a previous step)
    selected_recipe_id: Optional[str]
    # For per-user filtering, auditing, etc.
    user_id: str

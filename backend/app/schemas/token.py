from typing import Optional

from pydantic import BaseModel


class RefreshRequest(BaseModel):
    refresh_token: str


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str | None = None


class TokenPayload(BaseModel):
    sub: Optional[str] = None  # Subject (user ID)
    exp: Optional[int] = None  # Expiration time

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, verify_password
from app.repos.user import UserRepository
from app.schemas.token import Token


async def login_user(db: AsyncSession, email: str, password: str) -> Token:
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(email)
    if not user or not verify_password(password, str(user.hashed_password)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inactive user")
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

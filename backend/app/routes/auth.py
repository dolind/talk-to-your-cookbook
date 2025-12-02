from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import decode_token
from app.database.init_db import get_db
from app.schemas.token import RefreshRequest, Token
from app.schemas.user import UserCreate
from app.services import auth, users

router = APIRouter()


@router.post("/token", response_model=Token)  # pragma: no cover
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    token = await auth.login_user(db, form_data.username, form_data.password)
    return token


@router.post("/refresh", response_model=Token)  # pragma: no cover
async def refresh_access_token(body: RefreshRequest):
    payload = decode_token(body.refresh_token, expected_type="refresh")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    new_access_token = auth.create_access_token({"sub": user_id})
    new_refresh_token = auth.create_refresh_token({"sub": user_id})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)  # pragma: no cover
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await users.register_user(db, user_in)
    access_token = auth.create_access_token({"sub": str(user.id)})
    refresh_token = auth.create_refresh_token({"sub": str(user.id)})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/test-token")  # pragma: no cover
async def test_token(current_user=Depends(get_current_user)):
    return {"email": current_user.email, "message": "Token is valid"}


@router.post("/logout")  # pragma: no cover
def logout():
    return {"message": "Successfully logged out"}

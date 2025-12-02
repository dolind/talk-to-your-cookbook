from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate
from app.services.auth import login_user
from app.services.users import register_user


async def register_and_get_token(authed_client) -> Token:
    email = f"user_{uuid4()}@test.com"
    password = "strongpassword"

    # Register
    await authed_client.post(
        "/api/v1/auth/register", json={"email": email, "password": password, "first_name": "T", "last_name": "U"}
    )

    # Login
    response = await authed_client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return Token.model_validate(response.json())


@pytest.mark.asyncio
async def test_register_and_login_service(db_session):
    user_in = UserCreate(email="test_user@example.com", password="password", first_name="T", last_name="U")
    user = await register_user(db_session, user_in)
    assert user.email == user_in.email

    token = await login_user(db_session, user_in.email, user_in.password)
    assert isinstance(token, Token)


@pytest.mark.system
@pytest.mark.asyncio
async def test_token_verification(authed_client_session, db_session):
    token = await register_and_get_token(authed_client_session)

    response = await authed_client_session.post(
        "/api/v1/auth/test-token", headers={"Authorization": f"Bearer {token.access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Token is valid"
    assert "email" in data


@pytest.mark.asyncio
async def test_login_wrong_password_service(db_session):
    user = User(email="wrongpass@test.com", hashed_password=get_password_hash("correctpass"))
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(HTTPException, match="Incorrect email or password"):
        await login_user(db_session, "wrongpass@test.com", "incorrectpass")


@pytest.mark.asyncio
async def test_register_duplicate_email_service(db_session):
    email = "duplicate@test.com"
    user = User(email=email, hashed_password="x")
    db_session.add(user)
    await db_session.commit()

    user_in = UserCreate(email=email, password="newpasswrd", first_name="F", last_name="L")
    with pytest.raises(ValueError, match="already exists"):
        await register_user(db_session, user_in)


@pytest.mark.asyncio
async def test_logout(authed_client_session):
    response = await authed_client_session.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"

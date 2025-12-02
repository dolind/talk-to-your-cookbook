import json

import pytest

from app.core.security import get_password_hash
from app.models.user import User


@pytest.mark.asyncio
async def test_get_current_user_info(authed_client, db_session, auth_as_user):
    user = User(
        email="user_2@test.com",
        hashed_password=get_password_hash("strongpass"),
        first_name="Bob",
        last_name="Brown",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    async with auth_as_user(user):
        response = await authed_client.get("/api/v1/users/me", headers={"Authorization": "Bearer dummytoken"})

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == user.email
    assert data["first_name"] == "Bob"


@pytest.mark.asyncio
async def test_update_current_user(authed_client, db_session, auth_as_user):
    user = User(
        email="user_3@test.com",
        hashed_password=get_password_hash("strongpass"),
        first_name="Old",
        last_name="Name",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    async with auth_as_user(user):
        response = await authed_client.put(
            "/api/v1/users/me",
            json={"first_name": "New", "last_name": "Name"},
        )

    assert response.status_code == 200
    assert response.json()["first_name"] == "New"


@pytest.mark.asyncio
async def test_update_preferences(authed_client, db_session, auth_as_user):
    user = User(
        email="user_4@test.com",
        hashed_password=get_password_hash("strongpass"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    preferences = {
        "dietary_preferences": ["low_carb", "vegan"],
        "allergens": ["nuts", "gluten"],
        "nutrition_targets": {"protein": 180},
    }

    async with auth_as_user(user):
        response = await authed_client.put("/api/v1/users/me/preferences", json=preferences)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["dietary_preferences"] == preferences["dietary_preferences"]
    assert data["allergens"] == preferences["allergens"]
    assert data["nutrition_targets"] == preferences["nutrition_targets"]


@pytest.mark.asyncio
async def test_get_preferences(authed_client, db_session, auth_as_user):
    user = User(
        email="user_5@test.com",
        hashed_password=get_password_hash("strongpass"),
        is_active=True,
        dietary_preferences=json.dumps({"low_carb": True}),
        allergens=json.dumps({"dairy": True}),
        nutrition_targets=json.dumps({"protein": 150}),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    async with auth_as_user(user):
        response = await authed_client.get("/api/v1/users/me/preferences")

    assert response.status_code == 200
    data = response.json()
    assert data["dietary_preferences"]["low_carb"] is True
    assert data["allergens"]["dairy"] is True
    assert data["nutrition_targets"]["protein"] == 150


@pytest.mark.asyncio
async def test_update_user_email_conflict(authed_client, db_session, auth_as_user):
    owner = User(email="owner@test.com", hashed_password="pw", is_active=True)
    other = User(email="taken@test.com", hashed_password="pw", is_active=True)
    db_session.add_all([owner, other])
    await db_session.commit()
    await db_session.refresh(owner)

    async with auth_as_user(owner):
        res = await authed_client.put(
            "/api/v1/users/me",
            json={"email": "taken@test.com"},
        )

    assert res.status_code == 400


@pytest.mark.asyncio
async def test_get_preferences_empty(authed_client, db_session, auth_as_user):
    user = User(email="pref@test.com", hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    async with auth_as_user(user):
        res = await authed_client.get("/api/v1/users/me/preferences")

    assert res.status_code == 200
    assert res.json() == {
        "dietary_preferences": None,
        "allergens": None,
        "nutrition_targets": None,
    }

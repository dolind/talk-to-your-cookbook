import json

import pytest

from app.models.user import User
from app.schemas.user import UserCreate, UserPreferencesUpdate, UserUpdate
from app.services import users


class FakeUserRepo:
    def __init__(self, existing_emails=None):
        self.existing_emails = set(existing_emails or [])
        self.created_users = []
        self.updated_users = []

    async def exists_by_email(self, email: str) -> bool:
        return email in self.existing_emails

    async def create(self, user: User) -> User:
        self.created_users.append(user)
        return user

    async def update(self, user: User) -> User:
        self.updated_users.append(user)
        return user


@pytest.mark.asyncio
async def test_register_user_raises_when_email_exists(monkeypatch):
    fake_repo = FakeUserRepo(existing_emails={"exists@example.com"})
    monkeypatch.setattr(users, "UserRepository", lambda db: fake_repo)

    user_in = UserCreate(
        email="exists@example.com",
        password="longenough",
        first_name="Test",
        last_name="User",
    )

    with pytest.raises(ValueError, match="already exists"):
        await users.register_user(db=None, user_in=user_in)

    assert fake_repo.created_users == []


@pytest.mark.asyncio
async def test_register_user_hashes_password_and_creates(monkeypatch):
    fake_repo = FakeUserRepo()
    monkeypatch.setattr(users, "UserRepository", lambda db: fake_repo)
    monkeypatch.setattr(users, "get_password_hash", lambda password: f"hashed-{password}")

    user_in = UserCreate(
        email="new@example.com",
        password="supersecret",
        first_name="New",
        last_name="User",
    )

    created_user = await users.register_user(db=None, user_in=user_in)

    assert created_user.hashed_password == "hashed-supersecret"
    assert fake_repo.created_users == [created_user]
    assert created_user.email == "new@example.com"
    assert created_user.is_active is True
    assert created_user.is_admin is False


@pytest.mark.asyncio
async def test_update_user_updates_fields_and_hashes_password(monkeypatch):
    fake_repo = FakeUserRepo()
    monkeypatch.setattr(users, "UserRepository", lambda db: fake_repo)
    monkeypatch.setattr(users, "get_password_hash", lambda password: f"hashed-{password}")

    db_user = User(
        email="old@example.com",
        hashed_password="old-hash",
        first_name="Old",
        last_name="Name",
    )
    update = UserUpdate(
        email="new@example.com",
        password="newpassword",
        first_name="New",
        last_name="Name",
    )

    updated_user = await users.update_user(db=None, db_user=db_user, update=update)

    assert updated_user.email == "new@example.com"
    assert updated_user.first_name == "New"
    assert updated_user.last_name == "Name"
    assert updated_user.hashed_password == "hashed-newpassword"
    assert fake_repo.updated_users == [db_user]


@pytest.mark.asyncio
async def test_update_user_rejects_duplicate_email(monkeypatch):
    fake_repo = FakeUserRepo(existing_emails={"taken@example.com"})
    monkeypatch.setattr(users, "UserRepository", lambda db: fake_repo)

    db_user = User(
        email="current@example.com",
        hashed_password="hash",
        first_name="First",
        last_name="Last",
    )
    update = UserUpdate(email="taken@example.com")

    with pytest.raises(ValueError, match="Email already in use"):
        await users.update_user(db=None, db_user=db_user, update=update)

    assert db_user.email == "current@example.com"
    assert fake_repo.updated_users == []


@pytest.mark.asyncio
async def test_update_preferences_serializes_lists_and_dict(monkeypatch):
    fake_repo = FakeUserRepo()
    monkeypatch.setattr(users, "UserRepository", lambda db: fake_repo)

    db_user = User(email="prefs@example.com", hashed_password="hash")
    prefs = UserPreferencesUpdate(
        dietary_preferences=["vegan", "keto"],
        allergens=["nuts"],
        nutrition_targets={"calories": 2000},
    )

    updated_user = await users.update_preferences(db=None, db_user=db_user, prefs=prefs)

    assert updated_user.dietary_preferences == json.dumps(["vegan", "keto"])
    assert updated_user.allergens == json.dumps(["nuts"])
    assert updated_user.nutrition_targets == json.dumps({"calories": 2000})
    assert fake_repo.updated_users == [db_user]


@pytest.mark.asyncio
async def test_update_preferences_preserves_existing_when_missing(monkeypatch):
    fake_repo = FakeUserRepo()
    monkeypatch.setattr(users, "UserRepository", lambda db: fake_repo)

    db_user = User(
        email="keep@example.com",
        hashed_password="hash",
        dietary_preferences='["vegan"]',
        allergens='["gluten"]',
        nutrition_targets='{"protein": 100}',
    )
    prefs = UserPreferencesUpdate()

    updated_user = await users.update_preferences(db=None, db_user=db_user, prefs=prefs)

    assert updated_user.dietary_preferences == '["vegan"]'
    assert updated_user.allergens == '["gluten"]'
    assert updated_user.nutrition_targets == '{"protein": 100}'
    assert fake_repo.updated_users == [db_user]

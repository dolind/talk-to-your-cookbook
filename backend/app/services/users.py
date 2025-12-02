import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User
from app.repos.user import UserRepository
from app.schemas.user import UserCreate, UserPreferencesUpdate, UserUpdate


async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
    user_repo = UserRepository(db)
    if await user_repo.exists_by_email(str(user_in.email)):
        raise ValueError("A user with this email already exists")

    db_user = User(
        email=str(user_in.email),
        hashed_password=get_password_hash(user_in.password),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        is_active=True,
        is_admin=False,
    )
    return await user_repo.create(db_user)


async def update_user(db: AsyncSession, db_user: User, update: UserUpdate) -> User:
    user_repo = UserRepository(db)
    if update.first_name:
        db_user.first_name = update.first_name
    if update.last_name:
        db_user.last_name = update.last_name
    if update.email and update.email != db_user.email:
        if await user_repo.exists_by_email(update.email):
            raise ValueError("Email already in use")
        db_user.email = update.email
    if update.password:
        db_user.hashed_password = get_password_hash(update.password)
    return await user_repo.update(db_user)


async def update_preferences(db: AsyncSession, db_user: User, prefs: UserPreferencesUpdate) -> User:
    user_repo = UserRepository(db)
    if prefs.dietary_preferences:
        db_user.dietary_preferences = json.dumps(prefs.dietary_preferences)
    if prefs.allergens:
        db_user.allergens = json.dumps(prefs.allergens)
    if prefs.nutrition_targets:
        db_user.nutrition_targets = json.dumps(prefs.nutrition_targets)
    return await user_repo.update(db_user)

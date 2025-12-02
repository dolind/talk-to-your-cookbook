import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_recipe_repo
from app.database.init_db import get_db
from app.models.user import User
from app.repos.recipe import RecipeRepository
from app.schemas.user import UserPreferencesUpdate, UserResponse, UserUpdate
from app.services import users

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await users.update_user(db, current_user, user_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/me/preferences", response_model=UserResponse)
async def update_user_prefs(
    prefs: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await users.update_preferences(db, current_user, prefs)


@router.get("/me/preferences")
async def get_prefs(current_user: User = Depends(get_current_user)):
    return {
        "dietary_preferences": json.loads(current_user.dietary_preferences or "null"),
        "allergens": json.loads(current_user.allergens or "null"),
        "nutrition_targets": json.loads(current_user.nutrition_targets or "null"),
    }


@router.get("/me/stats")
async def profile_stats(
    current_user: User = Depends(get_current_user), recipe_repo: RecipeRepository = Depends(get_recipe_repo)
):
    # Count recipes
    recipes = await recipe_repo.list(owner_id=current_user.id, skip=0, limit=99999)
    items = recipes["items"]

    total_recipes = len(items)

    # Count images
    image_count = sum(1 for r in items if r.image_url)

    # Tags frequency
    tag_map = {}
    for r in items:
        for t in r.tags or []:
            tag_map[t] = tag_map.get(t, 0) + 1
    top_tags = sorted(tag_map.items(), key=lambda x: x[1], reverse=True)[:10]

    # Categories distribution
    cat_map = {}
    for r in items:
        for c in r.categories or []:
            cat_map[c] = cat_map.get(c, 0) + 1

    # Creation dates (for chart)
    by_date = {}
    for r in items:
        d = r.created_at.date().isoformat()
        by_date[d] = by_date.get(d, 0) + 1

    # Storage size
    import os

    total_size = 0
    for r in items:
        if r.image_url and os.path.exists(r.image_url):
            total_size += os.path.getsize(r.image_url)

    return {
        "total_recipes": total_recipes,
        "images": image_count,
        "top_tags": top_tags,
        "categories": cat_map,
        "dates": by_date,
        "storage_bytes": total_size,
        "user": {
            "email": current_user.email,
            "created_at": current_user.created_at,
        },
    }

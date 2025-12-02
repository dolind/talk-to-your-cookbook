from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, status

from app.core.deps import get_current_user, get_meal_plan_repo
from app.models.meal_plan import MealType
from app.models.user import User
from app.repos.meal_plan import MealPlanRepository
from app.schemas.meal_plan import (
    MealPlanCreate,
    MealPlanPage,
    MealPlanRead,
    MealPlanUpdate,
)

router = APIRouter()


@router.post("/", response_model=MealPlanRead, status_code=status.HTTP_201_CREATED)
async def create_meal_plan(
    meal_plan_in: MealPlanCreate,
    repo: MealPlanRepository = Depends(get_meal_plan_repo),
    current_user: User = Depends(get_current_user),
):
    return await repo.add(owner_id=current_user.id, data=meal_plan_in)


@router.get("/", response_model=MealPlanPage)
async def list_meal_plans(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    repo: MealPlanRepository = Depends(get_meal_plan_repo),
    current_user: User = Depends(get_current_user),
):
    return await repo.list(
        owner_id=current_user.id,
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/current", response_model=MealPlanRead)
async def current_meal_plan(
    repo: MealPlanRepository = Depends(get_meal_plan_repo),
    current_user: User = Depends(get_current_user),
):
    return await repo.get_current(owner_id=current_user.id)


@router.get("/{meal_plan_id}", response_model=MealPlanRead)
async def get_meal_plan(
    meal_plan_id: str,
    repo: MealPlanRepository = Depends(get_meal_plan_repo),
    current_user: User = Depends(get_current_user),
):
    return await repo.get_visible(meal_plan_id, viewer_id=current_user.id)  # pragma: no cover


@router.put("/{meal_plan_id}", response_model=MealPlanRead)
async def update_meal_plan(
    meal_plan_id: str,
    meal_plan_in: MealPlanUpdate,
    repo: MealPlanRepository = Depends(get_meal_plan_repo),
    current_user: User = Depends(get_current_user),
):
    return await repo.update(meal_plan_id=meal_plan_id, owner_id=current_user.id, patch=meal_plan_in)


@router.delete("/{meal_plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_plan(
    meal_plan_id: str,
    repo: MealPlanRepository = Depends(get_meal_plan_repo),
    current_user: User = Depends(get_current_user),
):
    await repo.delete(meal_plan_id, owner_id=current_user.id)


@router.post("/generate", response_model=MealPlanRead)
async def generate_meal_plan(
    start_date: date = Body(...),
    days: int = Body(..., ge=1, le=14),
    meals_per_day: List[MealType] = Body(...),
    max_prep_time: Optional[int] = Body(None),
    preferred_categories: Optional[List[str]] = Body(None),
    excluded_categories: Optional[List[str]] = Body(None),
    repo: MealPlanRepository = Depends(get_meal_plan_repo),
    current_user: User = Depends(get_current_user),
):
    return await repo.generate(
        owner_id=current_user.id,
        start_date=start_date,
        days=days,
        meals_per_day=meals_per_day,
        max_prep_time=max_prep_time,
        preferred_categories=preferred_categories,
        excluded_categories=excluded_categories,
    )


@router.get("/{meal_plan_id}/shopping-list")
async def shopping_list(
    meal_plan_id: str,
    repo: MealPlanRepository = Depends(get_meal_plan_repo),
    current_user: User = Depends(get_current_user),
):
    return await repo.shopping_list(meal_plan_id, owner_id=current_user.id)  # pragma: no cover

from datetime import date

from fastapi import APIRouter, Depends, status

from app.core.deps import get_current_user, get_shopping_list_repo
from app.models.meal_plan import MealType
from app.models.user import User
from app.repos.shopping_list import ShoppingListRepository
from app.schemas.shopping_list import (
    ShoppingListItemCreate,
    ShoppingListItemRead,
    ShoppingListItemUpdate,
    ShoppingListRead,
)
from app.services.shopping_list_service import ShoppingListService

router = APIRouter()


def get_shopping_list_service(
    repo: ShoppingListRepository = Depends(get_shopping_list_repo),
) -> ShoppingListService:
    return ShoppingListService(repo)  # pragma: no cover


shopping_list_service = ShoppingListService(Depends(get_shopping_list_repo))


@router.get("/", response_model=ShoppingListRead)  # pragma: no cover
async def get_shopping_list(
    current_user: User = Depends(get_current_user),
    service: ShoppingListService = Depends(get_shopping_list_service),
):
    return await service.get_shopping_list_read(user_id=current_user.id)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)  # pragma: no cover
async def clear_shopping_list(
    repo: ShoppingListRepository = Depends(get_shopping_list_repo),
    current_user: User = Depends(get_current_user),
):
    """Delete all items in the user's shopping list."""
    await repo.clear_shopping_list(current_user.id)


# ------------------------ Items ------------------------


@router.post("/items", response_model=ShoppingListItemRead, status_code=status.HTTP_201_CREATED)  # pragma: no cover
async def add_shopping_list_item(
    item: ShoppingListItemCreate,
    repo: ShoppingListRepository = Depends(get_shopping_list_repo),
    current_user: User = Depends(get_current_user),
):
    """Add a new manual shopping list item."""
    return await repo.add_item(user_id=current_user.id, item=item)


@router.patch("/items/{item_id}", response_model=ShoppingListItemRead)  # pragma: no cover
async def update_shopping_list_item(
    item_id: str,
    update: ShoppingListItemUpdate,
    repo: ShoppingListRepository = Depends(get_shopping_list_repo),
    current_user: User = Depends(get_current_user),
):
    """Update a shopping list item (e.g., toggle checked)."""
    return await repo.update_item(user_id=current_user.id, item_id=item_id, update=update)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)  # pragma: no cover
async def delete_shopping_list_item(
    item_id: str,
    repo: ShoppingListRepository = Depends(get_shopping_list_repo),
    current_user: User = Depends(get_current_user),
):
    """Delete a specific item from the shopping list."""
    await repo.delete_item(user_id=current_user.id, item_id=item_id)


# ------------------------ Contextual Deletes ------------------------


@router.delete("/by-recipe/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)  # pragma: no cover
async def remove_items_by_recipe(
    recipe_id: str,
    repo: ShoppingListRepository = Depends(get_shopping_list_repo),
    current_user: User = Depends(get_current_user),
):
    """Delete all items added from a specific recipe."""
    await repo.remove_by_recipe(user_id=current_user.id, recipe_id=recipe_id)


@router.delete("/by-meal-plan/{meal_plan_id}", status_code=status.HTTP_204_NO_CONTENT)  # pragma: no cover
async def remove_items_by_meal_plan(
    meal_plan_id: str,
    repo: ShoppingListRepository = Depends(get_shopping_list_repo),
    current_user: User = Depends(get_current_user),
):
    """Delete all items imported from a meal plan."""
    await repo.remove_by_meal_plan(user_id=current_user.id, meal_plan_id=meal_plan_id)


@router.delete("/by-meal-plan-recipe", status_code=status.HTTP_204_NO_CONTENT)  # pragma: no cover
async def remove_items_by_meal_plan_recipe(
    meal_plan_id: str,
    day: date,
    meal_type: str,
    recipe_id: str,
    repo: ShoppingListRepository = Depends(get_shopping_list_repo),
    current_user: User = Depends(get_current_user),
):
    """Remove a recipe's ingredients from a specific meal in a plan and update the plan."""
    await repo.remove_by_meal_plan_recipe(
        user_id=current_user.id,
        meal_plan_id=meal_plan_id,
        day=day,
        meal_type=MealType(meal_type),
        recipe_id=recipe_id,
    )


# ------------------------ Imports ----------------------------------


@router.post("/import-recipe", status_code=status.HTTP_201_CREATED)  # pragma: no cover
async def import_recipe_to_shopping_list(
    recipe_id: str,
    repo: ShoppingListRepository = Depends(get_shopping_list_repo),
    current_user: User = Depends(get_current_user),
):
    """Import all ingredients from a recipe into the shopping list."""
    await repo.import_recipe(user_id=current_user.id, recipe_id=recipe_id)


@router.post("/import-meal-plan", status_code=status.HTTP_201_CREATED)  # pragma: no cover
async def import_meal_plan_to_shopping_list(
    meal_plan_id: str,
    repo: ShoppingListRepository = Depends(get_shopping_list_repo),
    current_user: User = Depends(get_current_user),
):
    """Import all ingredients from all recipes in a meal plan."""
    await repo.import_meal_plan(user_id=current_user.id, meal_plan_id=meal_plan_id)

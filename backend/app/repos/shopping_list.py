from datetime import date
from fractions import Fraction
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.meal_plan import MealPlan, MealType
from app.models.recipe import Recipe
from app.models.shopping_list import ShoppingList, ShoppingListItem
from app.schemas.shopping_list import (
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
)


def parse_quantity(qty: str | float | None) -> float | None:
    if qty is None:
        return None
    if isinstance(qty, (int, float)):
        return float(qty)
    try:
        return float(Fraction(qty))
    except (ValueError, ZeroDivisionError):
        return None  # or raise an error/log warning


class ShoppingListRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_shopping_list(self, user_id: str) -> ShoppingList:
        stmt = (
            select(ShoppingList)
            .where(ShoppingList.owner_id == user_id)
            .options(selectinload(ShoppingList.items))  # ensure eager load
        )
        result = await self.db.execute(stmt)
        sl = result.scalar_one_or_none()

        if not sl:
            sl = ShoppingList(id=str(uuid4()), owner_id=user_id, name="My Shopping List")
            self.db.add(sl)
            await self.db.flush()
            await self.db.refresh(sl)
        return sl

    async def clear_shopping_list(self, user_id: str):
        stmt = delete(ShoppingListItem).where(
            ShoppingListItem.shopping_list_id.in_(select(ShoppingList.id).where(ShoppingList.owner_id == user_id))
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def add_item(self, user_id: str, item: ShoppingListItemCreate):
        sl = await self.get_shopping_list(user_id)
        new_item = ShoppingListItem(
            shopping_list_id=sl.id,
            ingredient_name=item.ingredient_name,
            quantity=item.quantity,
            unit=item.unit,
            checked=False,
        )
        self.db.add(new_item)
        await self.db.commit()
        await self.db.refresh(new_item)
        return new_item

    async def update_item(self, user_id: str, item_id: str, update: ShoppingListItemUpdate):
        sl = await self.get_shopping_list(user_id)
        stmt = select(ShoppingListItem).where(
            ShoppingListItem.id == item_id, ShoppingListItem.shopping_list_id == sl.id
        )
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        for field, value in update.model_dump(exclude_unset=True).items():
            setattr(item, field, value)

        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_item(self, user_id: str, item_id: str):
        sl = await self.get_shopping_list(user_id)
        stmt = delete(ShoppingListItem).where(
            ShoppingListItem.id == item_id, ShoppingListItem.shopping_list_id == sl.id
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def remove_by_recipe(self, user_id: str, recipe_id: str):
        sl = await self.get_shopping_list(user_id)
        stmt = delete(ShoppingListItem).where(
            ShoppingListItem.shopping_list_id == sl.id, ShoppingListItem.recipe_id == recipe_id
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def remove_by_meal_plan(self, user_id: str, meal_plan_id: str):
        sl = await self.get_shopping_list(user_id)
        stmt = delete(ShoppingListItem).where(
            ShoppingListItem.shopping_list_id == sl.id, ShoppingListItem.meal_plan_id == meal_plan_id
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def remove_by_meal_plan_recipe(
        self, user_id: str, meal_plan_id: str, day: date, meal_type: MealType, recipe_id: str
    ):
        sl = await self.get_shopping_list(user_id)
        stmt = delete(ShoppingListItem).where(
            ShoppingListItem.shopping_list_id == sl.id,
            ShoppingListItem.meal_plan_id == meal_plan_id,
            ShoppingListItem.meal_plan_day == day,
            ShoppingListItem.meal_type == meal_type,
            ShoppingListItem.recipe_id == recipe_id,
        )
        await self.db.execute(stmt)

        # Optionally update meal plan to remove the recipe
        update_stmt = (
            select(MealPlan)
            .where(MealPlan.id == meal_plan_id, MealPlan.user_id == user_id)
            .options(selectinload(MealPlan.days))
        )
        result = await self.db.execute(update_stmt)
        plan = result.scalar_one_or_none()

        if plan:
            for d in plan.days:
                if d.date == day:
                    d.items = [i for i in d.items if i.recipe_id != recipe_id or i.meal_type != meal_type]

        await self.db.commit()

    async def import_recipe(self, user_id: str, recipe_id: str):
        recipe_stmt = (
            select(Recipe)
            .where(Recipe.id == recipe_id, Recipe.user_id == user_id)
            .options(selectinload(Recipe.ingredients))
        )
        result = await self.db.execute(recipe_stmt)
        recipe = result.scalar_one_or_none()

        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        sl = await self.get_shopping_list(user_id)

        for ing in recipe.ingredients:
            self.db.add(
                ShoppingListItem(
                    shopping_list_id=sl.id,
                    ingredient_name=ing.name,
                    quantity=parse_quantity(ing.quantity),
                    unit=ing.unit,
                    recipe_id=recipe.id,
                    checked=False,
                )
            )

        await self.db.commit()

    async def import_meal_plan(self, user_id: str, meal_plan_id: str):
        plan_stmt = (
            select(MealPlan)
            .where(MealPlan.id == meal_plan_id, MealPlan.user_id == user_id)
            .options(selectinload(MealPlan.days))
        )
        result = await self.db.execute(plan_stmt)
        plan = result.scalar_one_or_none()

        if not plan:
            raise HTTPException(status_code=404, detail="Meal plan not found")

        recipe_ids = {i.recipe_id for d in plan.days for i in d.items if i.recipe_id}
        if not recipe_ids:
            raise HTTPException(status_code=400, detail="No recipes in meal plan")

        recipe_stmt = (
            select(Recipe)
            .where(Recipe.id.in_(recipe_ids), Recipe.user_id == user_id)
            .options(selectinload(Recipe.ingredients))
        )
        recipes = (await self.db.execute(recipe_stmt)).scalars().all()
        recipe_map = {r.id: r for r in recipes}

        sl = await self.get_shopping_list(user_id)

        for day in plan.days:
            for item in day.items:
                recipe = recipe_map.get(item.recipe_id)
                if not recipe:
                    continue
                for ing in recipe.ingredients:
                    self.db.add(
                        ShoppingListItem(
                            shopping_list_id=sl.id,
                            ingredient_name=ing.name,
                            quantity=parse_quantity(ing.quantity),
                            unit=ing.unit,
                            recipe_id=recipe.id,
                            meal_plan_id=meal_plan_id,
                            meal_plan_day=day.date.isoformat(),
                            meal_type=item.meal_type,
                            note=item.notes,
                            checked=False,
                        )
                    )

        await self.db.commit()

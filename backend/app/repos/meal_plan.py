from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.meal_plan import MealPlan, MealPlanDay, MealPlanItem, MealType
from app.models.recipe import Recipe
from app.schemas.meal_plan import MealPlanCreate, MealPlanUpdate

FULL_LOAD = (
    selectinload(MealPlan.days)
    .selectinload(MealPlanDay.items)
    .selectinload(MealPlanItem.recipe)
    .selectinload(Recipe.ingredients),
    selectinload(MealPlan.days)
    .selectinload(MealPlanDay.items)
    .selectinload(MealPlanItem.recipe)
    .selectinload(Recipe.nutrition),
    selectinload(MealPlan.days)
    .selectinload(MealPlanDay.items)
    .selectinload(MealPlanItem.recipe)
    .selectinload(Recipe.instructions),
)


def _base(owner_id: Optional[str] = None):
    stmt = select(MealPlan).options(*FULL_LOAD)
    if owner_id:
        stmt = stmt.where(MealPlan.user_id == owner_id)
    return stmt


class MealPlanRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─────────── helpers ────────────

    async def _count(self, stmt):
        return await self.db.scalar(select(func.count()).select_from(stmt.subquery()))

    async def _must_get_owned(self, pid: str, owner_id: str) -> MealPlan:
        plan = (await self.db.execute(_base().where(MealPlan.id == pid))).scalars().first()
        if not plan:
            raise HTTPException(404, "Meal plan not found")
        if plan.user_id != owner_id:
            raise HTTPException(403, "Not allowed")
        return plan

    # ─────────── CRUD ───────────────
    async def add(self, owner_id: str, data: MealPlanCreate) -> MealPlan:
        await self._validate_recipes(data, owner_id)

        plan = MealPlan(
            user_id=owner_id,
            name=data.name,
            description=data.description,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        for day in data.days:
            d = MealPlanDay(date=day.date, notes=day.notes)
            for itm in day.items:
                d.items.append(
                    MealPlanItem(
                        recipe_id=itm.recipe_id,
                        meal_type=itm.meal_type,
                        servings=itm.servings,
                        notes=itm.notes,
                    )
                )
            plan.days.append(d)

        self.db.add(plan)
        await self.db.commit()
        return await self.get(plan.id, owner_id)

    async def list(
        self,
        *,
        owner_id: str,
        skip: int,
        limit: int,
        start_date: Optional[date],
        end_date: Optional[date],
    ):
        stmt = _base(owner_id)
        if start_date:
            stmt = stmt.filter(MealPlan.end_date >= start_date)
        if end_date:
            stmt = stmt.filter(MealPlan.start_date <= end_date)
        stmt = stmt.order_by(MealPlan.start_date.desc())

        total = await self._count(stmt)
        items = (await self.db.execute(stmt.offset(skip).limit(limit))).scalars().all()
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    async def get(self, pid: str, owner_id: str) -> Optional[MealPlan]:
        return (await self.db.execute(_base(owner_id).where(MealPlan.id == pid))).scalars().first()

    async def get_visible(self, pid: str, viewer_id: str):
        plan = (await self.db.execute(_base().where(MealPlan.id == pid))).scalars().first()
        if not plan:
            raise HTTPException(404, "Meal plan not found")
        if plan.user_id != viewer_id:
            raise HTTPException(403, "Not allowed")
        return plan

    async def get_current(self, *, owner_id: str):
        today = date.today()
        stmt = _base(owner_id).where(MealPlan.start_date <= today, MealPlan.end_date >= today)
        plan = (await self.db.execute(stmt)).scalars().first()
        if not plan:
            raise HTTPException(404, "No meal plan found for the current date")
        return plan

    async def update(self, meal_plan_id: str, owner_id: str, patch: MealPlanUpdate) -> MealPlan:
        plan = await self._must_get_owned(meal_plan_id, owner_id)

        if patch.name is not None:
            plan.name = patch.name
        if patch.description is not None:
            plan.description = patch.description
        if patch.start_date is not None:
            plan.start_date = patch.start_date
        if patch.end_date is not None:
            plan.end_date = patch.end_date

        if patch.days is not None:
            await self._validate_recipes(patch, owner_id)

            # delete existing days
            await self.db.execute(delete(MealPlanDay).where(MealPlanDay.meal_plan_id == plan.id))
            plan.days = []
            for d in patch.days:
                day = MealPlanDay(date=d.date, notes=d.notes)
                for itm in d.items:
                    day.items.append(
                        MealPlanItem(
                            recipe_id=itm.recipe_id,
                            meal_type=itm.meal_type,
                            servings=itm.servings,
                            notes=itm.notes,
                        )
                    )
                plan.days.append(day)

        plan.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return await self.get(plan.id, owner_id)

    async def delete(self, meal_plan_id: str, *, owner_id: str):
        plan = await self._must_get_owned(meal_plan_id, owner_id)
        await self.db.delete(plan)
        await self.db.commit()

    # ─────────── generate & shopping list ─────────
    async def generate(
        self,
        *,
        owner_id: str,
        start_date: date,
        days: int,
        meals_per_day: List[MealType],
        max_prep_time: Optional[int],
        preferred_categories: Optional[List[str]],
        excluded_categories: Optional[List[str]],
    ):
        end_date = start_date + timedelta(days=days - 1)
        plan = MealPlan(
            user_id=owner_id,
            name=f"Meal Plan {start_date} to {end_date}",
            start_date=start_date,
            end_date=end_date,
            description="Auto-generated",
        )

        # find available recipes
        stmt = select(Recipe).where(Recipe.user_id == owner_id)
        if max_prep_time is not None:
            stmt = stmt.filter(Recipe.prep_time <= max_prep_time)
        if preferred_categories:
            stmt = stmt.filter(or_(*(Recipe.categories.contains(c) for c in preferred_categories)))
        if excluded_categories:
            for c in excluded_categories:
                stmt = stmt.filter(~Recipe.categories.contains(c))

        recipes = (await self.db.execute(stmt)).scalars().all()
        if not recipes:
            raise HTTPException(400, "No recipes found matching constraints")

        for offset in range(days):
            current = start_date + timedelta(days=offset)
            d = MealPlanDay(date=current)
            for mt in meals_per_day:
                recipe = random.choice(recipes)
                d.items.append(MealPlanItem(recipe_id=recipe.id, meal_type=mt, servings=1))
            plan.days.append(d)

        self.db.add(plan)
        await self.db.commit()
        return await self.get(plan.id, owner_id)

    async def shopping_list(self, meal_plan_id: str, *, owner_id: str):
        plan = await self._must_get_owned(meal_plan_id, owner_id)

        recipe_ids = [itm.recipe_id for d in plan.days for itm in d.items]  # flat list
        stmt = select(Recipe).options(selectinload(Recipe.ingredients)).where(Recipe.id.in_(recipe_ids))
        recipes = (await self.db.execute(stmt)).scalars().all()

        sl: dict[str, dict] = {}
        for r in recipes:
            for ing in r.ingredients:
                key = ing.name.strip().lower()
                if key not in sl:
                    sl[key] = {
                        "name": ing.name,
                        "quantity": ing.quantity,
                        "unit": ing.unit,
                        "recipes": [r.title],
                    }
                else:
                    if sl[key]["unit"] == ing.unit and ing.quantity and sl[key]["quantity"]:
                        try:
                            sl[key]["quantity"] = str(float(sl[key]["quantity"]) + float(ing.quantity))
                        except ValueError:
                            # fallback to string concat if non-numeric
                            sl[key]["quantity"] += ing.quantity
                    if r.title not in sl[key]["recipes"]:
                        sl[key]["recipes"].append(r.title)

        items = sorted(sl.values(), key=lambda x: x["name"])
        return {
            "meal_plan_id": meal_plan_id,
            "meal_plan_name": plan.name,
            "start_date": plan.start_date,
            "end_date": plan.end_date,
            "items": items,
        }

    # ─────────── validation ──────────
    async def _validate_recipes(self, obj: MealPlanCreate | MealPlanUpdate, owner_id: str):
        """Ensure every referenced recipe exists & belongs to the owner."""
        recipe_ids = {itm.recipe_id for d in obj.days for itm in d.items if itm.recipe_id}

        if not recipe_ids:
            return
        stmt = select(Recipe.id).where(Recipe.id.in_(recipe_ids), Recipe.user_id == owner_id)
        found = set((await self.db.execute(stmt)).scalars().all())
        missing = recipe_ids - found
        if missing:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Recipes {missing} not found or not yours",
            )

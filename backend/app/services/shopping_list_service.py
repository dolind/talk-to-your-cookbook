# put here as the logic to construct a nested shopping list became to complex for endpoint
from collections import defaultdict

from sqlalchemy import select

from app.models.meal_plan import MealPlan
from app.models.recipe import Recipe
from app.repos.shopping_list import ShoppingListRepository
from app.schemas.shopping_list import ImportedMealPlan, ImportedRecipe, ShoppingListItemRead, ShoppingListRead


class ShoppingListService:
    def __init__(self, repo: ShoppingListRepository):
        self.repo = repo  # Store reference to the repo

    async def get_shopping_list_read(self, user_id: str) -> ShoppingListRead:
        shopping_list = await self.repo.get_shopping_list(user_id)

        items = [ShoppingListItemRead.model_validate(i) for i in shopping_list.items]

        # Grouping for imported_recipes
        recipe_groups = defaultdict(list)
        for i in shopping_list.items:
            if i.recipe_id:
                recipe_groups[i.recipe_id].append(i)

        recipe_ids = list(recipe_groups.keys())

        # should be done different as the service should not get direct database access
        recipes = await self.repo.db.execute(select(Recipe).where(Recipe.id.in_(recipe_ids)))
        recipe_map = {r.id: r for r in recipes.scalars()}

        imported_recipes = [
            ImportedRecipe(
                recipe_id=rid,
                title=recipe_map.get(rid).title if recipe_map.get(rid) else "Unknown Recipe",
            )
            for rid in recipe_groups
        ]

        # Grouping for imported_meal_plans
        meal_plan_groups = defaultdict(list)
        for i in shopping_list.items:
            if i.meal_plan_id:
                key = (i.meal_plan_id, i.meal_plan_day, i.meal_type)
                meal_plan_groups[key].append(i)

        meal_plan_ids = {meal_plan_id for (meal_plan_id, _, _) in meal_plan_groups.keys()}

        plans = await self.repo.db.execute(select(MealPlan).where(MealPlan.id.in_(meal_plan_ids)))
        meal_plan_map = {p.id: p for p in plans.scalars()}

        imported_meal_plans = [
            ImportedMealPlan(
                meal_plan_id=meal_plan_id,
                name=(
                    f"Week of {p.start_date.strftime('%b %-d')}–{p.end_date.strftime('%b %-d, %Y')}"
                    if p
                    else "Unnamed Plan"
                ),
            )
            for meal_plan_id, p in meal_plan_map.items()
        ]

        return ShoppingListRead(
            items=items,
            imported_recipes=imported_recipes,
            imported_meal_plans=imported_meal_plans,
        )

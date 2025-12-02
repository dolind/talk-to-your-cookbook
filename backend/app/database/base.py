# Import all the models here so Alembic can detect them
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so they are registered with the Base metadata
# from app.database.models.user import User  # noqa
# from app.database.models.recipe import Recipe, RecipeIngredient, RecipeInstruction, RecipeNutrition, RecipeVector  # noqa
# from app.database.models.meal_plan import MealPlan, MealPlanDay, MealPlanItem  # noqa
# from app.database.models.chat import ChatSession, ChatMessage  # noqa
# from app.database.models.recent_recipe import RecentRecipe  # noqa

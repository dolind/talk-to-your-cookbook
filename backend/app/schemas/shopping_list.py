from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.meal_plan import MealType


class ShoppingListItemBase(BaseModel):
    ingredient_name: str = Field(..., examples=["Tomatoes"])
    quantity: Optional[float] = Field(None, examples=[2])
    unit: Optional[str] = Field(None, examples=["pcs"])


class ShoppingListItemCreate(ShoppingListItemBase):
    pass


class ShoppingListItemUpdate(ShoppingListItemBase):
    ingredient_name: Optional[str] = None
    checked: Optional[bool] = None


class ShoppingListItemRead(ShoppingListItemBase):
    id: str
    recipe_title: Optional[str] = None
    checked: bool
    recipe_id: Optional[str] = None
    note: Optional[str] = None
    meal_plan_id: Optional[str] = None
    meal_plan_day: Optional[date] = None  # e.g. '2025-07-01'
    meal_plan_name: Optional[str] = None  # e.g. '2025-07-01'
    meal_type: Optional[MealType] = None
    checked: Optional[bool] = None
    model_config = {"from_attributes": True}


class ImportedRecipe(BaseModel):
    recipe_id: str
    title: str


class ImportedMealPlan(BaseModel):
    meal_plan_id: str
    name: str


class ShoppingListRead(BaseModel):
    items: List[ShoppingListItemRead]
    imported_recipes: List[ImportedRecipe] = []
    imported_meal_plans: List[ImportedMealPlan] = []
    model_config = {"from_attributes": True}

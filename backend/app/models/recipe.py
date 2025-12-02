from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base
from app.models.model_helper import generate_uuid

if TYPE_CHECKING:
    from app.models.meal_plan import MealPlanItem
    from app.models.recent_recipe import RecentRecipe
    from app.models.user import User


class Recipe(Base):
    __tablename__ = "recipes"

    # we use str, not uuid as we test with sqlite, and might pivot later
    id: Mapped[str] = mapped_column(primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    prep_time: Mapped[int | None] = mapped_column()
    cook_time: Mapped[int | None] = mapped_column()
    servings: Mapped[int | None] = mapped_column(SmallInteger)
    image_url: Mapped[str | None] = mapped_column()
    source: Mapped[str | None] = mapped_column()
    source_url: Mapped[str | None] = mapped_column()
    categories: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_public: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    difficulty: Mapped[str | None] = mapped_column()
    notes: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[int | None] = mapped_column(SmallInteger, index=True)

    user: Mapped["User"] = relationship(back_populates="recipes")
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", lazy="selectin"
    )
    instructions: Mapped[list["RecipeInstruction"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", lazy="selectin"
    )
    nutrition: Mapped["RecipeNutrition | None"] = relationship(
        back_populates="recipe", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )

    meal_plan_items: Mapped[list["MealPlanItem"]] = relationship(back_populates="recipe", lazy="selectin")
    recent_recipes: Mapped[list["RecentRecipe"]] = relationship(back_populates="recipe", lazy="selectin")

    # runs: Mapped[list["RecipeRecordORM"]] = relationship("RecipeRecordORM", back_populates="recipe", lazy="selectin")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[str] = mapped_column(primary_key=True, default=generate_uuid)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    order: Mapped[int] = mapped_column(SmallInteger)
    name: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[Optional[str]] = mapped_column(String)
    unit: Mapped[Optional[str]] = mapped_column(String)
    preparation: Mapped[Optional[str]] = mapped_column(String)
    notes: Mapped[Optional[str]] = mapped_column(String)

    # Relationship
    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients", lazy="selectin")


class RecipeInstruction(Base):
    __tablename__ = "recipe_instructions"

    id: Mapped[str] = mapped_column(primary_key=True, default=generate_uuid)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    step: Mapped[int] = mapped_column(SmallInteger)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)

    recipe: Mapped["Recipe"] = relationship(back_populates="instructions", lazy="selectin")


class RecipeNutrition(Base):
    __tablename__ = "recipe_nutrition"

    id: Mapped[str] = mapped_column(primary_key=True, default=generate_uuid)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, unique=True)
    calories: Mapped[Optional[float]] = mapped_column(Float)
    protein: Mapped[Optional[float]] = mapped_column(Float)
    carbohydrates: Mapped[Optional[float]] = mapped_column(Float)
    fat: Mapped[Optional[float]] = mapped_column(Float)
    fiber: Mapped[Optional[float]] = mapped_column(Float)
    sugar: Mapped[Optional[float]] = mapped_column(Float)
    sodium: Mapped[Optional[float]] = mapped_column(Float)
    additional_data: Mapped[Optional[dict]] = mapped_column(Text)

    recipe: Mapped["Recipe"] = relationship(back_populates="nutrition")

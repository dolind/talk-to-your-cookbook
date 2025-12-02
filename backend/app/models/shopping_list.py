from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

# if TYPE_CHECKING:
from app.models.meal_plan import MealType
from app.models.model_helper import generate_uuid
from app.models.recipe import Recipe


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id: Mapped[str] = mapped_column(primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    items: Mapped[list["ShoppingListItem"]] = relationship(
        back_populates="list", cascade="all, delete-orphan", lazy="selectin"
    )


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id: Mapped[str] = mapped_column(primary_key=True, default=generate_uuid)
    shopping_list_id: Mapped[str] = mapped_column(ForeignKey("shopping_lists.id"), nullable=False)

    ingredient_name: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[Optional[float]] = mapped_column(Float)
    unit: Mapped[Optional[str]] = mapped_column(String)
    checked: Mapped[bool] = mapped_column(Boolean, default=False)

    # 🧠 Backtrace info
    recipe_id: Mapped[Optional[str]] = mapped_column(ForeignKey("recipes.id"))
    meal_plan_id: Mapped[Optional[str]] = mapped_column(ForeignKey("meal_plans.id"))
    meal_plan_day: Mapped[Optional[str]] = mapped_column(String)  # ISO date as string
    meal_type: Mapped[Optional[MealType]] = mapped_column(Enum(MealType))

    note: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    list: Mapped[ShoppingList] = relationship(back_populates="items")
    recipe: Mapped[Optional["Recipe"]] = relationship(lazy="selectin")

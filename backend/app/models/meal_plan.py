import enum
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.recipe import Recipe

from app.models.model_helper import generate_uuid


class MealType(enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[str] = mapped_column(primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="meal_plans")
    days: Mapped[list["MealPlanDay"]] = relationship(
        back_populates="meal_plan", cascade="all, delete-orphan", lazy="selectin"
    )


class MealPlanDay(Base):
    __tablename__ = "meal_plan_days"
    id: Mapped[str] = mapped_column(primary_key=True, default=generate_uuid)
    meal_plan_id: Mapped[str] = mapped_column(ForeignKey("meal_plans.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    meal_plan: Mapped["MealPlan"] = relationship(back_populates="days", lazy="selectin")
    items: Mapped[list["MealPlanItem"]] = relationship(
        back_populates="day", cascade="all, delete-orphan", lazy="selectin", passive_deletes=True
    )


class MealPlanItem(Base):
    __tablename__ = "meal_plan_items"

    id: Mapped[str] = mapped_column(primary_key=True, default=generate_uuid)
    day_id: Mapped[str] = mapped_column(ForeignKey("meal_plan_days.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[Optional[str]] = mapped_column(ForeignKey("recipes.id"))
    meal_type: Mapped[MealType] = mapped_column(Enum(MealType), nullable=False)
    servings: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    day: Mapped["MealPlanDay"] = relationship(back_populates="items", lazy="selectin")
    recipe: Mapped[Optional["Recipe"]] = relationship(back_populates="meal_plan_items", lazy="selectin")

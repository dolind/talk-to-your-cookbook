from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base
from app.models.chat import ChatSession
from app.models.meal_plan import MealPlan
from app.models.model_helper import generate_uuid
from app.models.recent_recipe import RecentRecipe
from app.models.recipe import Recipe

if TYPE_CHECKING:
    from app.models.ocr import BookScanORM


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String)
    last_name: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Preferences (stored as JSON strings)
    dietary_preferences: Mapped[Optional[str]] = mapped_column(Text)
    allergens: Mapped[Optional[str]] = mapped_column(Text)
    nutrition_targets: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    recipes: Mapped[list["Recipe"]] = relationship(back_populates="user")
    meal_plans: Mapped[list["MealPlan"]] = relationship(back_populates="user")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user")
    recent_recipes: Mapped[list["RecentRecipe"]] = relationship(back_populates="user")
    book_scans: Mapped[list["BookScanORM"]] = relationship("BookScanORM", back_populates="user")

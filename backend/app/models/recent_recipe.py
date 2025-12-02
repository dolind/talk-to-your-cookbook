from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.recipe import Recipe
    from app.models.user import User
from app.models.model_helper import generate_uuid


class RecentRecipe(Base):
    __tablename__ = "recent_recipes"

    id: Mapped[str] = mapped_column(primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    recipe_id: Mapped[str] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    used_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="recent_recipes")
    recipe: Mapped["Recipe"] = relationship(back_populates="recent_recipes")

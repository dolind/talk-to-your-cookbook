from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, model_validator


class MealType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class MealPlanItemBase(BaseModel):
    recipe_id: Optional[str] = None
    recipe_name: Optional[str] = None
    meal_type: MealType
    servings: Optional[int] = 1
    notes: Optional[str] = None


class MealPlanItemCreate(MealPlanItemBase):
    pass


class MealPlanItemUpdate(MealPlanItemBase):
    pass


class MealPlanItemRead(MealPlanItemBase):
    id: str
    day_id: str
    model_config = {"from_attributes": True}


class MealPlanDayBase(BaseModel):
    date: date
    notes: Optional[str] = None


class MealPlanDayCreate(MealPlanDayBase):
    items: List[MealPlanItemCreate] = []


class MealPlanDayUpdate(MealPlanDayBase):
    items: List[MealPlanItemUpdate] = []


class MealPlanDayRead(MealPlanDayBase):
    id: str
    meal_plan_id: str
    items: List[MealPlanItemRead] = []
    model_config = {"from_attributes": True}


class MealPlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def check_dates(self) -> "MealPlanBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class MealPlanCreate(MealPlanBase):
    days: List[MealPlanDayCreate] = []


class MealPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: Optional[List[MealPlanDayUpdate]] = None

    @model_validator(mode="after")
    def check_dates(self) -> "MealPlanUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class MealPlanRead(MealPlanBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    days: List[MealPlanDayRead] = []
    model_config = {"from_attributes": True}


class MealPlanPage(BaseModel):
    items: List[MealPlanRead]
    total: int
    skip: int
    limit: int

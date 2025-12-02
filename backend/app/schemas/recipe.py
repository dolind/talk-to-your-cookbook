import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class RecipeIngredientBase(BaseModel):
    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None
    preparation: Optional[str] = None


class RecipeIngredientCreate(RecipeIngredientBase):
    pass


class RecipeIngredientUpdate(RecipeIngredientBase):
    name: Optional[str]


class RecipeIngredientRead(RecipeIngredientBase):
    id: str
    recipe_id: str
    order: int
    model_config = {"from_attributes": True}


class RecipeInstructionBase(BaseModel):
    step: int
    instruction: str

    class Config:
        from_attributes = True


class RecipeInstructionCreate(RecipeInstructionBase):
    pass


class RecipeInstructionUpdate(BaseModel):
    step: int = None
    instruction: str = None


class RecipeInstructionRead(RecipeInstructionBase):
    pass


class RecipeDeleteRequest(BaseModel):
    ids: List[str]


class RecipeNutritionBase(BaseModel):
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbohydrates: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    additional_data: Optional[Dict[str, Any]] = None


class RecipeNutritionCreate(RecipeNutritionBase):
    pass


class RecipeNutritionUpdate(RecipeNutritionBase):
    pass


class RecipeNutritionRead(RecipeNutritionBase):
    id: str
    recipe_id: str
    model_config = {"from_attributes": True}

    @field_validator("additional_data", mode="before")
    @classmethod
    def parse_additional_data(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        if v is None:
            return {}
        return v


class RecipeBase(BaseModel):
    title: str
    description: Optional[str] = None
    prep_time: Optional[int] = None  # in minutes
    cook_time: Optional[int] = None  # in minutes
    servings: Optional[int] = None
    image_url: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    categories: Optional[List[str]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)

    difficulty: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None
    nutritional_info: Optional[str] = None

    ingredients: Optional[List[RecipeIngredientCreate]] = Field(default_factory=list)
    instructions: Optional[List[RecipeInstructionCreate]] = Field(default_factory=list)
    nutrition: Optional[RecipeNutritionBase] = None


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(RecipeBase):
    title: Optional[str] = None
    delete_image: Optional[bool] = None
    ingredients: Optional[List[RecipeIngredientUpdate]] = Field(default_factory=list)
    instructions: Optional[List[RecipeInstructionUpdate]] = Field(default_factory=list)


class RecipeRead(RecipeBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    ingredients: List[RecipeIngredientRead] = []
    instructions: List[RecipeInstructionRead]
    nutrition: Optional[RecipeNutritionRead] = None
    model_config = {"from_attributes": True}

    @field_validator("categories", "tags", mode="before")
    @classmethod
    def parse_json_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v


class RecipePage(BaseModel):
    items: List[RecipeRead]
    total: Optional[int] = None
    skip: Optional[int] = None
    limit: Optional[int] = None
    hasMore: Optional[bool] = None


class RecipeSearchParams(BaseModel):
    search_term: Optional[str] = None
    categories: Optional[List[str]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)
    max_prep_time: Optional[int] = None
    min_calories: Optional[float] = None
    max_calories: Optional[float] = None
    sort_by: Optional[str] = "created_at"  # created_at, title, prep_time
    sort_asc: Optional[bool] = False


class RecipeFilterOptions(BaseModel):
    categories: List[str]
    sources: List[str]

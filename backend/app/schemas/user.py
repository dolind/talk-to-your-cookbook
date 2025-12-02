import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class UserBase(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @field_validator("password")
    def password_strength(cls, v):
        # Simple password strength check
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    @field_validator("password")
    def password_strength(cls, v):
        # Check password strength if a password is provided
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserPreferencesUpdate(BaseModel):
    dietary_preferences: Optional[List[str]] = None
    allergens: Optional[List[str]] = None
    nutrition_targets: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    id: str
    created_at: datetime

    dietary_preferences: Optional[List[str]] = None
    allergens: Optional[List[str]] = None
    nutrition_targets: Optional[Dict[str, Any]] = None

    @field_validator("dietary_preferences", "allergens", mode="before")
    def parse_json_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

    @field_validator("nutrition_targets", mode="before")
    def parse_json_dict(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

    class Config:
        from_attributes = True

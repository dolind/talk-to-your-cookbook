from abc import ABC, abstractmethod
from typing import Any, Dict

from app.schemas.recipe import RecipeCreate


class ValidationService(ABC):
    """Contract for turning OCR text into a structured recipe."""

    @abstractmethod
    async def validate(self, classification: Dict[str, Any], thumbnail_filename: str) -> RecipeCreate:
        """
        Accept OCR blocks and return any JSON‑serialisable structure
        describing the recipe.
        """
        ...

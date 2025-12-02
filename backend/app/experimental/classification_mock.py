from __future__ import annotations

from typing import Any, Dict

from app.ports.classification import ClassificationService
from app.schemas.ocr import OCRResult


class MockClassificationService(ClassificationService):  # pragma: no cover
    """Deterministic stub used in tests & local dev."""

    async def classify(self, ocr_blocks: list[Dict[str, Any]], ocr_result: OCRResult | None) -> Dict[str, Any]:
        # Ignore input, return a fixed recipe JSON
        return {
            "title": "Chocolate Cake",
            "description": "Rich and moist chocolate cake.",
            "prep_time": "1 h 15 m",
            "cook_time": "45m",
            "servings": "8",
            "difficulty": "Medium",
            "categories": ["Dessert"],
            "tags": ["cake", "chocolate"],
            "ingredients": [
                {"name": "Flour", "quantity": "2", "unit": "cups"},
                {"name": "Sugar", "quantity": "1.5", "unit": "cups"},
                {"name": "Cocoa powder", "quantity": "0.5", "unit": "cup"},
            ],
            "instructions": [
                {"step": 1, "instruction": "Preheat oven to 350 °F."},
                {"step": 2, "instruction": "Mix dry ingredients."},
                {"step": 3, "instruction": "Add wet ingredients and mix."},
                {"step": 4, "instruction": "Bake for 45 minutes."},
            ],
            "nutrition": {
                "calories": 400,
                "protein": 6,
                "fat": 15,
                "carbohydrates": 60,
            },
        }

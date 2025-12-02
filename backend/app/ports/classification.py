from abc import ABC, abstractmethod
from typing import Any, Dict

from app.schemas.ocr import OCRResult


class ClassificationService(ABC):
    """Contract for turning OCR text into a structured recipe."""

    @abstractmethod
    async def classify(self, ocr_blocks: list[Dict[str, Any]], ocr_result: OCRResult | None) -> Dict[str, Any]:
        """
        Accept OCR blocks and return any JSON‑serialisable structure
        describing the recipe.
        """
        ...

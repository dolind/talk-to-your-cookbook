from typing import Any, Dict

from app.ports.classification import ClassificationService
from app.ports.recipe_parser_llm import RecipeParserLLM
from app.schemas.ocr import OCRResult


class ClassificationSimple(ClassificationService):
    """Deterministic stub used in tests & local dev."""

    def __init__(self, parser: RecipeParserLLM):
        self.parser: RecipeParserLLM = parser

    async def classify(self, ocr_blocks: list[Dict[str, Any]], ocr_result: OCRResult | None) -> Dict[str, Any]:
        if ocr_result:
            full_text = ocr_result.full_text
            return await self.parser.parse(full_text)
        else:
            return {}

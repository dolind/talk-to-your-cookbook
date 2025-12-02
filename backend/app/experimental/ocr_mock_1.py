import json
from typing import Any, Dict

from app.ports.ocr import OCRService
from app.schemas.ocr import OCRResult


class MockOCRService(OCRService):  # pragma: no cover
    def __init__(self, mock_response_path: str):
        self.mock_response_path = mock_response_path

    async def extract(self, image_path: str, image_id: str) -> OCRResult:
        # Load mock response directly
        with open(self.mock_response_path, "r", encoding="utf-8") as f:
            raw_result: Dict[str, Any] = json.load(f)

        # Extract fullTextAnnotation directly
        full_text_annotation = raw_result.get("fullTextAnnotation", {})
        full_text = full_text_annotation.get("text", "")
        pages = full_text_annotation.get("pages", [])
        blocks = pages[0].get("blocks", []) if pages else []

        return OCRResult(page_id=image_id, blocks=blocks, full_text=full_text)

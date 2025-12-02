from app.ports.ocr import OCRService
from app.schemas.ocr import OCRResult


class SuperSimpleOCRMockService(OCRService):  # pragma: no cover
    async def extract(self, image_path: str, image_id: str) -> OCRResult:
        full_text = "WAITING?\nPLEASE\nTURN OFF\nYOUR\nENGINE\n"

        result = OCRResult(page_id=image_id, full_text=full_text, blocks=[])
        return result

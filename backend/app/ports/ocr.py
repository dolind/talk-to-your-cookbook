from abc import ABC, abstractmethod

from app.schemas.ocr import OCRResult


class OCRService(ABC):
    @abstractmethod
    async def extract(self, image_path: str, image_id: str) -> OCRResult:
        """Runs OCR and returns a list of OCRBlock-like dictionaries."""
        ...


class TextOrImageService(ABC):
    @abstractmethod
    def is_text_page(self, filename: str) -> bool: ...

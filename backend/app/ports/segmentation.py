from abc import ABC, abstractmethod

from app.schemas.ocr import OCRResult, SegmentationResult


class SegmentationService(ABC):
    @abstractmethod
    async def segment(self, ocr_json: OCRResult, enable_segmentation: bool = False) -> SegmentationResult:
        """
        Return titles and the title blocks for the page
        """
        ...

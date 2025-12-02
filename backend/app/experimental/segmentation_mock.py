from app.ports.segmentation import SegmentationService
from app.schemas.ocr import OCRResult, SegmentationResult, SegmentationSegment


class NoSegmentationService(SegmentationService):  # pragma: no cover
    async def segment(self, ocr: OCRResult, enable_segmentation=False) -> SegmentationResult:
        # Return a single segment that spans all OCR blocks.
        # Mimics the one-page fallback path of SegmentationHeuristic.
        bounding_boxes = [block["boundingBox"]["vertices"] for block in ocr.blocks]
        associated = list(range(len(ocr.blocks)))

        segment = SegmentationSegment(
            id=0,
            title="",
            bounding_boxes=bounding_boxes,
            associated_ocr_blocks=associated,
        )

        return SegmentationResult(
            segmentation_done=False,
            page_segments=[segment],
        )

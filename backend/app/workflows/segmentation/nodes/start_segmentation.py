from app.schemas.ocr import SegmentationGraphState, SegmentationResult


async def start_segmentation(state: SegmentationGraphState, config) -> dict:
    segmentation_service = config["configurable"]["segmentation_service"]

    ocr_result = state.ocr_result

    segmentation: SegmentationResult = await segmentation_service.segment(ocr_result, True)

    return {"segmentation": segmentation}

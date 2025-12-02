import logging

from app.repos.image_repo import ImageRepository
from app.routes.status import broadcast_status
from app.schemas.ocr import GraphBroadCast, PageScanUpdate, PageStatus, SegmentationGraphState

logger = logging.getLogger(__name__)


async def approve_segmentation(state: SegmentationGraphState, config) -> dict:
    logger.info(f"Approving segmentation for {state.page_record_id}")
    page_id = state.page_record_id
    logger.info(f"Getting segmentation for {page_id}")
    segmentation = state.segmentation

    logger.info("Setting repo")
    page_repo: ImageRepository = config["configurable"]["page_repo"]
    logger.info(f"Updating page {page_id} with segments")
    await page_repo.update(
        PageScanUpdate(
            id=page_id,
            page_segments=segmentation.page_segments,
            segmentation_done=segmentation.segmentation_done,
            status=PageStatus.APPROVED,
        )
    )
    logger.info(f"Updated page {page_id}  with segments")
    await broadcast_status(GraphBroadCast(type="page", id=page_id, status=PageStatus.APPROVED))

    return {}

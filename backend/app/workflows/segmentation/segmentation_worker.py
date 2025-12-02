import asyncio
import logging

from app.ports.segmentation import SegmentationService
from app.ports.storage import StorageService
from app.repos.image_repo import ImageRepository
from app.routes.status import broadcast_status
from app.schemas.ocr import GraphBroadCast, PageScanRead, PageScanUpdate, PageStatus, SegmentationGraphState
from app.workflows.base_worker import BaseWorker
from app.workflows.segmentation.graph_builder import build_segmentation_graph

logger = logging.getLogger(__name__)
SEG_GRAPH = build_segmentation_graph()


class SegmentationWorker(BaseWorker[PageScanRead]):
    def __init__(
        self,
        seg_queue: asyncio.Queue[PageScanRead],
        image_repo: ImageRepository,
        segmentation_service: SegmentationService,
        storage: StorageService,
    ):
        (super().__init__(entry_queue=seg_queue),)
        self.seg = segmentation_service
        self.page_repo = image_repo
        self.storage = storage

    async def handle(self, next_page: PageScanRead):
        page_id = next_page.id
        logger.info(f"Processing image: {page_id}")

        # Load image from storage
        ocr_result = await self.storage.read_json(page_id)
        logger.info("Read OCR result from storage")
        state = SegmentationGraphState(
            page_record_id=page_id,
            ocr_result=ocr_result,
        )

        config = {
            "configurable": {
                "segmentation_service": self.seg,
                "storage": self.storage,
                "page_repo": self.page_repo,
                "thread_id": page_id,
            }
        }

        logger.debug("Invoking segmentation graph...")
        page = await self.page_repo.get(page_id)
        logger.info(f"Image: {page.page_type}")
        result = await SEG_GRAPH.ainvoke(state, config=config)
        logger.debug(f"Segmentation graph result: {result}")

        if result["__interrupt__"]:
            # we update the database with the preliminary segmentation, the frontend will request this data
            result = await self.page_repo.update(
                PageScanUpdate(
                    id=page_id,
                    status=PageStatus.NEEDS_REVIEW,
                    page_segments=result["segmentation"].page_segments,
                    segmentation_done=result["segmentation"].segmentation_done,
                )
            )
            logger.info(f"Finished segmentation for image of paget type {result.page_type}")
            await broadcast_status(GraphBroadCast(type="image", id=page_id, status=PageStatus.NEEDS_REVIEW))
            logger.info(f"Awaiting approval for image {page_id}")
        # We do not put into the next queue as all pages require segmentation before we continue
        else:
            logger.info(f"Finished segmentation for image {page_id}")

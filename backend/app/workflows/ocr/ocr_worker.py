import asyncio
import logging

from app.ports.ocr import OCRService, TextOrImageService
from app.ports.storage import StorageService
from app.repos.image_repo import ImageRepository
from app.routes.status import broadcast_status
from app.schemas.ocr import GraphBroadCast, OCRResult, PageScanRead, PageScanUpdate, PageStatus, PageType
from app.workflows.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class OCRWorker(BaseWorker[PageScanRead]):
    def __init__(
        self,
        ocr_queue: asyncio.Queue[PageScanRead],
        seg_queue: asyncio.Queue[PageScanRead],
        image_repo: ImageRepository,
        ocr_service: OCRService,
        storage: StorageService,
        text_or_image: TextOrImageService,
    ):
        (super().__init__(entry_queue=ocr_queue, worker_name="OCRWorker"),)
        self.entry_queue = ocr_queue
        self.exit_queue = seg_queue

        self.image_repo = image_repo
        self.ocr = ocr_service
        self.storage = storage
        self.page_classifier: TextOrImageService = text_or_image

    async def handle(self, next_image: PageScanRead):
        image_id = next_image.id
        logger.info(f"Processing image: {image_id}")

        image_path = await self.storage.get_image_path(image_id, "scanner")
        logger.debug(f"Image path: {image_path}")

        should_ocr = self.page_classifier.is_text_page(image_path)
        logger.info(f"{image_id} is text page: {should_ocr}")

        if should_ocr:
            ocr_result: OCRResult = await self.ocr.extract(image_path, image_id)
            page_type = PageType.TEXT
            status = PageStatus.OCR_DONE

            await self.storage.save_json(ocr_result.model_dump(), image_id)

            json_path = await self.storage.get_json_path(image_id)

        else:
            page_type = PageType.IMAGE
            status = PageStatus.APPROVED
            json_path = ""

        # Update image record
        dto = await self.image_repo.update(
            PageScanUpdate(id=image_id, ocr_path=json_path, status=status, page_type=page_type)
        )
        logger.info(f"page type is {dto.page_type}")
        # broadcast
        await broadcast_status(GraphBroadCast(type="image", id=image_id, status=status))

        # send text images to segmentation
        if page_type == PageType.TEXT:
            self.exit_queue.put_nowait(dto)

        logger.info(f"Finished OCR for {image_id} → {json_path}")

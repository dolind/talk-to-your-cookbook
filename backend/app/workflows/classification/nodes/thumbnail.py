import logging

from app.ports.storage import StorageService
from app.ports.thumbnail import ThumbnailService
from app.schemas.ocr import ClassificationGraphPatch, ClassificationGraphState, PageType

logger = logging.getLogger(__name__)


async def thumbnail_node(state: ClassificationGraphState, config) -> ClassificationGraphPatch:
    thumbnail_service: ThumbnailService = config["configurable"]["thumbnail_service"]
    storage: StorageService = config["configurable"]["storage"]

    text_pages = state.input_pages
    logger.info(f"Generating thumbnail for {text_pages}")

    image_id = next((p.original_id for p in text_pages if p.page_type == PageType.IMAGE), None)

    if not image_id:
        logger.info("No image pages available; skipping thumbnail generation.")
        return {"thumbnail_path": None}

    src_path = await storage.get_image_path(image_id, "scanner")
    thumb_bytes: bytes = await thumbnail_service.generate_thumbnail(src_path)

    thumb_filename = f"{image_id}_thumb.jpg"
    await storage.save_binary_image(thumb_bytes, thumb_filename, "scanner")

    return {"thumbnail_path": thumb_filename}

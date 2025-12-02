import logging
from typing import Any, Dict, List

from app.ports.classification import ClassificationService
from app.ports.storage import StorageService
from app.schemas.ocr import (
    ClassificationGraphPatch,
    ClassificationGraphState,
    ClassificationRecordInputPage,
    OCRResult,
    PageType,
)

logger = logging.getLogger(__name__)


async def start_classification(
    state: ClassificationGraphState,
    config,
) -> ClassificationGraphPatch:
    """Returns {'classification_result': ClassificationResult}"""
    svc: ClassificationService = config["configurable"]["classification_service"]
    storage: StorageService = config["configurable"]["storage"]
    text_pages: List[ClassificationRecordInputPage] = state.input_pages

    ocr_blocks: list[Dict[str, Any]] = []
    full_text_parts: list[str] = []
    base_result: OCRResult | None = None
    for page in text_pages:
        if page.page_type != PageType.TEXT:
            continue
        raw_data = await storage.read_json(page.original_id)
        parsed: OCRResult = OCRResult.model_validate(raw_data)
        if base_result is None:
            base_result = parsed
        page_blocks = parsed.blocks
        if page.segmentation_done:
            ocr_blocks.extend(page_blocks)
            full_text_parts.append(parsed.full_text)
        else:
            logger.warning(f"Using all blocks of page {page.original_id}")
            ocr_blocks.extend(page_blocks)
            full_text_parts.append(parsed.full_text)
    classified_json = await svc.classify(
        ocr_blocks, OCRResult(full_text="\n\n".join(full_text_parts), page_id=base_result.page_id, blocks=ocr_blocks)
    )

    return {"llm_candidate": classified_json}

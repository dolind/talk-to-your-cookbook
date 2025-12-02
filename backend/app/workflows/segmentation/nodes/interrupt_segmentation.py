import logging

from langgraph.types import interrupt

from app.schemas.ocr import SegmentationApproval, SegmentationGraphState

# Halts graph until frontend resumes via /approve

logger = logging.getLogger(__name__)


async def interrupt_segmentation(state: SegmentationGraphState) -> dict:
    """
    Pause so the user can edit the proposed segments (zones).
    We surface the segments to the front‑end; the front‑end will
    POST them back (edited or unchanged).
    """
    logger.info("interrupt_segmentation")
    # Pause graph, return payload
    interrupt_result = interrupt({"request_to_approve_seg": "payload in state"})

    user_response: SegmentationApproval = interrupt_result["response_to_approve_seg"]
    logger.info(user_response)

    seg_model = user_response.segmentation
    seg_dict = seg_model.model_dump()
    # Update state with final zones
    return {"segmentation": seg_dict}

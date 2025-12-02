import logging

from langgraph.types import interrupt

from app.schemas.ocr import ApprovedTaxonomyResult, ClassificationGraphPatch, ClassificationGraphState

logger = logging.getLogger(__name__)


async def interrupt_taxonomy(state: ClassificationGraphState) -> ClassificationGraphPatch:
    """
    Show suggested categories/tags; capture user’s confirmation/edits.
    """
    logger.info("Interrupt taxonomy")
    interrupt_result = interrupt({"request_to_approve_taxonomy": "payload in state"})
    logger.info(f"User categories{interrupt_result}")

    user_response: ApprovedTaxonomyResult = interrupt_result["response_to_approve_taxonomy"]

    return {"taxonomy_user_approved": {"categories": user_response.categories, "tags": user_response.tags}}

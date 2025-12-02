import logging

from langgraph.types import interrupt

from app.schemas.ocr import ClassificationGraphPatch, ClassificationGraphState, RecipeApproval

logger = logging.getLogger(__name__)


async def interrupt_classification(state: ClassificationGraphState) -> ClassificationGraphPatch:
    """
    Pause so the user can edit the proposed segments (zones).
    We surface the segments to the front‑end; the front‑end will
    POST them back (edited or unchanged).
    """

    # Pause graph, return payload
    interrupt_result = interrupt({"request_to_approve_llm": "payload in state"})
    logger.info(interrupt_result)
    user_response: RecipeApproval = interrupt_result["response_to_approve_llm"]

    if not user_response.approved:
        # user rejected — downstream can branch or stop
        return {"current_recipe_state": None}

    result = user_response.recipe if user_response.recipe is not None else state.current_recipe_state
    return {"current_recipe_state": result}

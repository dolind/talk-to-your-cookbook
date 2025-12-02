import logging

from app.ports.validation import ValidationService
from app.schemas.ocr import ClassificationGraphPatch, ClassificationGraphState
from app.schemas.recipe import RecipeCreate

logger = logging.getLogger(__name__)


async def validation_node(state: ClassificationGraphState, config) -> ClassificationGraphPatch:
    """
    First pass (no user_payload): validate LLM candidate and produce validation_result (dict for UI).
    Second pass (user_payload set): validate user edits and, if valid, produce approved_recipe (DTO);
    otherwise set revalidation_error so we loop back to the editor.
    """

    validation_service: ValidationService = config["configurable"]["validation_service"]
    logger.info("Validating")
    first_pass = state.current_recipe_state is None

    candidate = state.llm_candidate if first_pass else state.current_recipe_state.model_dump()

    if first_pass:
        logger.info(f"Validating LLM candidate for {candidate['title']}")
    else:
        logger.info(f"Validating user edits for {candidate['title']}")

    dto: RecipeCreate = await validation_service.validate(candidate, thumbnail_filename=state.thumbnail_path)
    logger.info("Validation finished")
    return {"current_recipe_state": dto, "first_pass_validation": first_pass}

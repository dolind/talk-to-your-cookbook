import logging

from app.ports.storage import StorageService
from app.repos.classification_record import ClassificationRecordRepository
from app.repos.recipe import RecipeRepository
from app.routes.status import broadcast_status
from app.schemas.ocr import (
    ClassificationGraphPatch,
    ClassificationGraphState,
    ClassificationRecordUpdate,
    GraphBroadCast,
    RecordStatus,
)

logger = logging.getLogger(__name__)


async def approve_classification(state: ClassificationGraphState, config) -> ClassificationGraphPatch:
    logger.info(f"Approving classification for {state.classification_record_id}")

    classification_repo: ClassificationRecordRepository = config["configurable"]["classification_repo"]
    storage: StorageService = config["configurable"]["storage"]

    recipe_repo: RecipeRepository = config["configurable"]["recipe_repo"]
    owner_id: str = config["configurable"]["owner_id"]
    logger.info(f"Creating recipe for classification record {state.classification_record_id}")
    logger.info(state.current_recipe_state.model_dump())
    try:
        recipe = state.current_recipe_state
        if recipe.image_url:
            await storage.copy_to_recipe(recipe.image_url)
        logger.info("Saved image")
        added_recipe = await recipe_repo.add(recipe, owner_id=owner_id)
        logger.info("Saved recipe")
        await classification_repo.update(
            ClassificationRecordUpdate(
                id=state.classification_record_id, status=RecordStatus.APPROVED, recipe_id=added_recipe.id
            )
        )
    except Exception as e:
        logger.error(f"Saving failed with {e}")

    logger.info(f"Updated record {state.classification_record_id}")
    await broadcast_status(
        GraphBroadCast(type="record", id=state.classification_record_id, status=RecordStatus.APPROVED)
    )

    return {}

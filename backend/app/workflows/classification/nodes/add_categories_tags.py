import logging

from app.repos.book import BookScanRepository
from app.schemas.ocr import ClassificationGraphPatch, ClassificationGraphState
from app.schemas.recipe import RecipeCreate
from app.workflows.classification.nodes.validate_or_merge_taxonomy import ALLOWED_CATEGORIES

logger = logging.getLogger(__name__)


async def enrich_categories_tags(state: ClassificationGraphState, config) -> ClassificationGraphPatch:
    """
    Suggest categories/tags from the (already approved) recipe.
    """
    logger.info("Adding categories/tags")
    recipe: RecipeCreate = state.current_recipe_state

    default_category = "Dinner" if "Dinner" in ALLOWED_CATEGORIES else sorted(ALLOWED_CATEGORIES)[0]
    cats = [default_category]
    tags = ["scanned"]

    recipe.tags = tags
    recipe.categories = cats
    book_repo: BookScanRepository = config["configurable"]["book_repo"]
    owner_id: str = config["configurable"]["owner_id"]

    book = await book_repo.get(state.book_scan_id, owner_id)
    recipe.source = book.title

    return {"current_recipe_state": recipe}

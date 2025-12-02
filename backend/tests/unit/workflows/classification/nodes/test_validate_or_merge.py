import pytest

from app.schemas.ocr import ClassificationGraphState
from app.schemas.recipe import RecipeCreate
from app.workflows.classification.nodes.validate_or_merge_taxonomy import validate_or_merge_taxonomy


@pytest.mark.asyncio
async def test_validate_or_merge_taxonomy_simple():
    recipe = RecipeCreate(title="t", categories=[], tags=[])
    state = ClassificationGraphState(
        current_recipe_state=recipe, taxonomy_user_approved={"categories": ["Dinner"], "tags": ["x"]}
    )
    out = await validate_or_merge_taxonomy(state)
    updated = out["current_recipe_state"]
    assert updated.categories == ["Dinner"]
    assert updated.tags == ["x"]

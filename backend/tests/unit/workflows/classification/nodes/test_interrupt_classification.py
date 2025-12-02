import pytest

from app.schemas.ocr import ClassificationGraphState, RecipeApproval
from app.schemas.recipe import RecipeCreate
from app.workflows.classification.nodes.interrupt_classification import interrupt_classification


@pytest.mark.asyncio
async def test_interrupt_classification_reject(monkeypatch):
    def fake_interrupt(payload):
        return {"response_to_approve_llm": RecipeApproval(approved=False)}

    monkeypatch.setattr(
        "app.workflows.classification.nodes.interrupt_classification.interrupt",
        fake_interrupt,
    )
    state = ClassificationGraphState()
    out = await interrupt_classification(state)
    assert out == {"current_recipe_state": None}


@pytest.mark.asyncio
async def test_interrupt_classification_accept(monkeypatch):
    recipe = RecipeCreate(title="A")

    def fake_interrupt(payload):
        return {"response_to_approve_llm": RecipeApproval(approved=True, recipe=recipe)}

    monkeypatch.setattr(
        "app.workflows.classification.nodes.interrupt_classification.interrupt",
        fake_interrupt,
    )
    state = ClassificationGraphState(current_recipe_state=None)

    out = await interrupt_classification(state)
    assert out["current_recipe_state"].title == "A"

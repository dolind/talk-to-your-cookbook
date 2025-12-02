import pytest

from app.schemas.ocr import ClassificationGraphState
from app.schemas.recipe import RecipeCreate
from app.workflows.classification.nodes.add_categories_tags import enrich_categories_tags


class FakeBookRepo:
    def __init__(self, book):
        self.book = book
        self.calls = []

    async def get(self, book_id, owner_id):
        self.calls.append((book_id, owner_id))
        return self.book


@pytest.mark.asyncio
async def test_enrich_categories_tags():
    recipe = RecipeCreate(title="t", categories=[], tags=[])
    state = ClassificationGraphState(
        current_recipe_state=recipe,
        book_scan_id="book1",
    )

    fake_repo = FakeBookRepo(book=type("Book", (), {"title": "My Book"}))
    cfg = {"configurable": {"book_repo": fake_repo, "owner_id": "u1"}}

    out = await enrich_categories_tags(state, cfg)

    updated = out["current_recipe_state"]
    assert updated.categories == ["Dinner"]  # default valid category
    assert updated.tags == ["scanned"]
    assert updated.source == "My Book"
    assert fake_repo.calls == [("book1", "u1")]

import pytest

from app.schemas.ocr import ClassificationGraphState
from app.schemas.recipe import RecipeCreate
from app.workflows.classification.nodes.approve_classification import approve_classification


class FakeStorage:
    def __init__(self):
        self.copied = []

    async def copy_to_recipe(self, path):
        self.copied.append(path)


class FakeRecipeRepo:
    def __init__(self, ret):
        self.ret = ret
        self.calls = []

    async def add(self, recipe, owner_id=None):
        self.calls.append((recipe, owner_id))
        return self.ret


class FakeClassRepo:
    def __init__(self):
        self.calls = []

    async def update(self, dto, owner_id=None):
        self.calls.append((dto, owner_id))


class FakeBroadcast:
    def __init__(self):
        self.calls = []

    async def __call__(self, msg):
        self.calls.append(msg)


@pytest.mark.asyncio
async def test_approve_classification(monkeypatch):
    storage = FakeStorage()
    recipe_repo = FakeRecipeRepo(ret=type("Added", (), {"id": "r1"}))
    class_repo = FakeClassRepo()
    fake_broadcast = FakeBroadcast()
    monkeypatch.setattr("app.workflows.classification.nodes.approve_classification.broadcast_status", fake_broadcast)

    recipe = RecipeCreate(title="X", image_url="img.jpg")
    state = ClassificationGraphState(
        classification_record_id="rec1",
        current_recipe_state=recipe,
    )

    cfg = {
        "configurable": {
            "classification_repo": class_repo,
            "storage": storage,
            "recipe_repo": recipe_repo,
            "owner_id": "u",
        }
    }

    out = await approve_classification(state, cfg)

    assert storage.copied == ["img.jpg"]
    assert len(recipe_repo.calls) == 1
    assert len(class_repo.calls) == 1
    assert out == {}
    assert len(fake_broadcast.calls) == 1

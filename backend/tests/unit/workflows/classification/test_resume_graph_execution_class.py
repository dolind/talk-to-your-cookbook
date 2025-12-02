import pytest

from app.schemas.ocr import (
    GroupApproval,
    RecipeApproval,
    RecordStatus,
)
from app.schemas.recipe import RecipeCreate
from app.workflows.classification.resume_graph_execution import resume_classification_graph

#
# -------------------------
# Fakes
# -------------------------
#


class FakeRepo:
    def __init__(self):
        self.updated = []

    async def update(self, update_dto, owner_id=None):
        self.updated.append((update_dto, owner_id))
        return update_dto


class FakeGraph:
    def __init__(self, result):
        self.calls = []
        self.result = result

    async def ainvoke(self, cmd, config):
        self.calls.append((cmd, config))
        return self.result


class FakeBroadcast:
    def __init__(self):
        self.calls = []

    async def __call__(self, msg):
        self.calls.append(msg)


#
# -------------------------
# Tests
# -------------------------
#


@pytest.mark.asyncio
async def test_resume_grouping_interrupt(monkeypatch):
    repo = FakeRepo()
    graph = FakeGraph(
        result={"__interrupt__": True, "current_recipe_state": RecipeCreate(title="A"), "thumbnail_path": "thumb"}
    )
    fake_broadcast = FakeBroadcast()

    monkeypatch.setattr(
        "app.workflows.classification.resume_graph_execution.CLASS_GRAPH",
        graph,
    )
    monkeypatch.setattr(
        "app.workflows.classification.resume_graph_execution.broadcast_status",
        fake_broadcast,
    )

    body = GroupApproval(approved=True, new_group=None)

    await resume_classification_graph(
        record_id="rec1",
        body=body,
        classification_repo=repo,
        validation_service=None,
        recipe_repo=None,
        storage=None,
        page_repo=None,
        book_repo=None,
        class_service=None,
        thumb_service=None,
        owner_id="u1",
    )

    # Repo updated
    assert len(repo.updated) == 1
    update_dto, owner = repo.updated[0]
    assert update_dto.status == RecordStatus.NEEDS_REVIEW

    # Broadcast happened
    assert len(fake_broadcast.calls) == 1


@pytest.mark.asyncio
async def test_resume_recipe_interrupt(monkeypatch):
    repo = FakeRepo()
    graph = FakeGraph(
        result={"__interrupt__": True, "current_recipe_state": RecipeCreate(title="A"), "thumbnail_path": "thumb"}
    )
    fake_broadcast = FakeBroadcast()

    monkeypatch.setattr(
        "app.workflows.classification.resume_graph_execution.CLASS_GRAPH",
        graph,
    )
    monkeypatch.setattr(
        "app.workflows.classification.resume_graph_execution.broadcast_status",
        fake_broadcast,
    )

    body = RecipeApproval(approved=True, recipe=None)

    await resume_classification_graph(
        record_id="rec1",
        body=body,
        classification_repo=repo,
        validation_service=None,
        recipe_repo=None,
        storage=None,
        page_repo=None,
        book_repo=None,
        class_service=None,
        thumb_service=None,
        owner_id="u1",
    )

    assert repo.updated[0][0].status == RecordStatus.NEEDS_TAXONOMY
    assert len(fake_broadcast.calls) == 1


@pytest.mark.asyncio
async def test_resume_no_interrupt(monkeypatch):
    repo = FakeRepo()
    graph = FakeGraph(result={"done": True})
    fake_broadcast = FakeBroadcast()

    monkeypatch.setattr(
        "app.workflows.classification.resume_graph_execution.CLASS_GRAPH",
        graph,
    )
    monkeypatch.setattr(
        "app.workflows.classification.resume_graph_execution.broadcast_status",
        fake_broadcast,
    )

    await resume_classification_graph(
        record_id="rec1",
        body=RecipeApproval(approved=True, recipe=None),
        classification_repo=repo,
        validation_service=None,
        recipe_repo=None,
        storage=None,
        page_repo=None,
        book_repo=None,
        class_service=None,
        thumb_service=None,
        owner_id="u1",
    )

    # No updates, no broadcast
    assert repo.updated == []
    assert fake_broadcast.calls == []

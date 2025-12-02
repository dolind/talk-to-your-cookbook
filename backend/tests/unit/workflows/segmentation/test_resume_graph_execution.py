import pytest
from langgraph.types import Command

from app.schemas.ocr import SegmentationApproval
from app.workflows.segmentation.resume_graph_execution import approve_segments


class FakeLock:
    def __init__(self):
        self.entered = 0
        self.exited = 0

    async def __aenter__(self):
        self.entered += 1

    async def __aexit__(self, *exc):
        self.exited += 1


class FakeSegGraph:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []

    async def ainvoke(self, command, config=None):
        self.calls.append((command, config))
        if self.exc:
            raise self.exc
        return self.result


class FakeRepo:
    pass


class FakeStorage:
    pass


@pytest.mark.asyncio
async def test_approve_segments_happy_path(monkeypatch):
    page_id = "p1"

    fake_lock = FakeLock()
    fake_graph = FakeSegGraph(result="ok")

    # provide SegmentationApproval object
    segmentation = SegmentationApproval(approved=True)

    # patch global _locks and SEG_GRAPH
    monkeypatch.setattr("app.workflows.segmentation.resume_graph_execution._locks", {page_id: fake_lock})
    monkeypatch.setattr("app.workflows.segmentation.resume_graph_execution.SEG_GRAPH", fake_graph)

    result = await approve_segments(
        page_id,
        segmentation,
        page_repo=FakeRepo(),
        storage=FakeStorage(),
    )

    # lock behavior
    assert fake_lock.entered == 1
    assert fake_lock.exited == 1

    # graph invocation
    assert len(fake_graph.calls) == 1
    cmd, cfg = fake_graph.calls[0]
    assert isinstance(cmd, Command)
    assert "response_to_approve_seg" in cmd.resume

    # return value
    assert result == {"message": f"Segmentation for {page_id} approved."}


@pytest.mark.asyncio
async def test_approve_segments_graph_error(monkeypatch):
    page_id = "p2"

    fake_lock = FakeLock()
    fake_graph = FakeSegGraph(exc=RuntimeError("graph failed"))

    monkeypatch.setattr("app.workflows.segmentation.resume_graph_execution._locks", {page_id: fake_lock})
    monkeypatch.setattr("app.workflows.segmentation.resume_graph_execution.SEG_GRAPH", fake_graph)

    segmentation = SegmentationApproval(approved=True)

    with pytest.raises(RuntimeError, match="graph failed"):
        await approve_segments(page_id, segmentation, FakeRepo(), FakeStorage())

    # lock was still used
    assert fake_lock.entered == 1
    assert fake_lock.exited == 1


@pytest.mark.asyncio
async def test_approve_segments_uses_lock(monkeypatch):
    """
    Confirms that the worker waits on the lock before calling SEG_GRAPH.
    """

    page_id = "p3"
    fake_lock = FakeLock()
    fake_graph = FakeSegGraph(result="ok")

    monkeypatch.setattr("app.workflows.segmentation.resume_graph_execution._locks", {page_id: fake_lock})
    monkeypatch.setattr("app.workflows.segmentation.resume_graph_execution.SEG_GRAPH", fake_graph)

    segmentation = SegmentationApproval(approved=True)

    await approve_segments(page_id, segmentation, FakeRepo(), FakeStorage())

    # The lock must have wrapped the call
    assert fake_lock.entered == 1
    assert fake_lock.exited == 1
    assert len(fake_graph.calls) == 1

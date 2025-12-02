import asyncio
from datetime import datetime

import pytest

from app.ports.segmentation import SegmentationService
from app.ports.storage import StorageService
from app.schemas.ocr import (
    OCRResult,
    PageScanRead,
    PageScanUpdate,
    PageStatus,
    PageType,
    SegmentationResult,
    SegmentationSegment,
)
from app.workflows.segmentation.segmentation_worker import SegmentationWorker

scanDate = datetime.now()


class FakeStorage(StorageService):
    def __init__(self):
        self.read_json_calls = []
        self.read_json_values = {}  # page_id -> OCRResult

    async def read_json(self, image_id: str):
        self.read_json_calls.append(image_id)
        if isinstance(self.read_json_values[image_id], Exception):
            raise self.read_json_values[image_id]
        return self.read_json_values[image_id]

    # ---- unused abstract methods ----
    async def save_image(self, *a, **k):
        raise NotImplementedError()

    async def save_binary_image(self, *a, **k):
        raise NotImplementedError()

    async def load_image(self, *a, **k):
        raise NotImplementedError()

    async def delete(self, *a, **k):
        raise NotImplementedError()

    async def rename(self, *a, **k):
        raise NotImplementedError()

    async def get_image_path(self, *a, **k):
        raise NotImplementedError()

    async def copy_to_recipe(self, *a, **k):
        raise NotImplementedError()

    async def get_json_path(self, *a, **k):
        raise NotImplementedError()

    async def save_json(self, *a, **k):
        raise NotImplementedError()

    def get_file_path(self, *a, **k):
        raise NotImplementedError()

    async def save_file(self, *a, **k):
        raise NotImplementedError()


class FakeSegmentationService(SegmentationService):
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.segment_calls = []

    async def segment(self, ocr_json: OCRResult, enable_segmentation: bool = False):
        self.segment_calls.append((ocr_json, enable_segmentation))
        if self.exc:
            raise self.exc
        return self.result


class FakeImageRepository:
    def __init__(self, pages=None, get_exc=None, update_exc=None, update_return=None):
        self.pages = pages or {}  # page_id -> PageScanRead
        self.get_exc = get_exc
        self.update_exc = update_exc
        self.update_return = update_return
        self.get_calls = []
        self.update_calls = []

    async def get(self, page_id: str):
        self.get_calls.append(page_id)
        if self.get_exc:
            raise self.get_exc
        return self.pages[page_id]

    async def update(self, dto: PageScanUpdate):
        self.update_calls.append(dto)
        if self.update_exc:
            raise self.update_exc
        return self.update_return


class FakeSegGraph:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []

    async def ainvoke(self, state, config=None):
        self.calls.append((state, config))
        if self.exc:
            raise self.exc
        return self.result


@pytest.mark.asyncio
async def test_segmentation_non_interrupt(monkeypatch):
    """
    SEG_GRAPH returns result with __interrupt__=False.
    No DB update, no broadcast.
    """

    page_id = "p100"
    page = PageScanRead(
        id=page_id,
        filename="p.jpg",
        bookScanID="b1",
        page_number=1,
        scanDate=scanDate,
        page_type=PageType.TEXT,
    )

    storage = FakeStorage()
    storage.read_json_values[page_id] = OCRResult(page_id=page_id, full_text="text", blocks=[])

    page_repo = FakeImageRepository(pages={page_id: page})
    seg_service = FakeSegmentationService()

    seg_graph_result = {"__interrupt__": False, "segmentation": None}
    fake_graph = FakeSegGraph(result=seg_graph_result)

    # Patch SEG_GRAPH
    monkeypatch.setattr("app.workflows.segmentation.segmentation_worker.SEG_GRAPH", fake_graph)

    # Capture broadcast calls
    broadcast_calls = {}

    async def fake_broadcast(msg):
        broadcast_calls["msg"] = msg

    monkeypatch.setattr(
        "app.workflows.segmentation.segmentation_worker.broadcast_status",
        fake_broadcast,
    )

    worker = SegmentationWorker(
        seg_queue=asyncio.Queue(),
        image_repo=page_repo,
        segmentation_service=seg_service,
        storage=storage,
    )

    await worker.handle(page)

    # read_json invoked
    assert storage.read_json_calls == [page_id]

    # repository.get invoked
    assert page_repo.get_calls == [page_id]

    # SEG_GRAPH invoked
    assert len(fake_graph.calls) == 1

    # no DB update
    assert page_repo.update_calls == []

    # no broadcast
    assert broadcast_calls == {}


@pytest.mark.asyncio
async def test_segmentation_interrupt_updates_and_broadcasts(monkeypatch):
    """
    SEG_GRAPH returns __interrupt__=True => repo.update + broadcast
    """

    page_id = "p200"
    page = PageScanRead(
        id=page_id,
        filename="p.jpg",
        bookScanID="b1",
        page_number=1,
        scanDate=scanDate,
        page_type=PageType.TEXT,
    )

    storage = FakeStorage()
    storage.read_json_values[page_id] = OCRResult(page_id=page_id, full_text="text", blocks=[])
    seg_segment = SegmentationSegment(
        id=1,
        title="t",
        bounding_boxes=[[{"x": 0, "y": 0}]],
        associated_ocr_blocks=[],
    )
    repo_return = PageScanRead(
        id=page_id,
        filename="p.jpg",
        bookScanID="b1",
        page_number=1,
        scanDate=scanDate,
        page_type=PageType.TEXT,
        status=PageStatus.NEEDS_REVIEW,
        page_segments=[seg_segment],
        segmentation_done=True,
    )

    page_repo = FakeImageRepository(
        pages={page_id: page},
        update_return=repo_return,
    )

    seg_service = FakeSegmentationService()

    seg_segment = SegmentationSegment(
        id=1,
        title="t",
        bounding_boxes=[[{"x": 0, "y": 0}]],
        associated_ocr_blocks=[],
    )

    seg_result_obj = SegmentationResult(
        page_segments=[seg_segment],
        segmentation_done=True,
    )

    fake_graph = FakeSegGraph(
        result={
            "__interrupt__": True,
            "segmentation": seg_result_obj,
        }
    )

    monkeypatch.setattr("app.workflows.segmentation.segmentation_worker.SEG_GRAPH", fake_graph)

    broadcast_calls = {}

    async def fake_broadcast(msg):
        broadcast_calls["msg"] = msg

    monkeypatch.setattr(
        "app.workflows.segmentation.segmentation_worker.broadcast_status",
        fake_broadcast,
    )

    worker = SegmentationWorker(
        seg_queue=asyncio.Queue(),
        image_repo=page_repo,
        segmentation_service=seg_service,
        storage=storage,
    )

    await worker.handle(page)

    # Storage load ok
    assert storage.read_json_calls == [page_id]

    # Repo get ok
    assert page_repo.get_calls == [page_id]

    # Graph called
    assert len(fake_graph.calls) == 1

    # Repo.update called once
    assert len(page_repo.update_calls) == 1
    dto = page_repo.update_calls[0]
    assert dto.id == page_id
    assert dto.status == PageStatus.NEEDS_REVIEW
    assert dto.page_segments == [seg_segment]
    assert dto.segmentation_done is True

    # broadcast emitted
    assert "msg" in broadcast_calls
    msg = broadcast_calls["msg"]
    assert msg.id == page_id
    assert msg.status == PageStatus.NEEDS_REVIEW


@pytest.mark.asyncio
async def test_segmentation_storage_read_error(monkeypatch):
    page_id = "p300"
    page = PageScanRead(
        id=page_id,
        filename="p.jpg",
        bookScanID="b1",
        page_number=1,
        scanDate=scanDate,
    )

    storage = FakeStorage()
    storage.read_json_values[page_id] = RuntimeError("read json failed")

    page_repo = FakeImageRepository(pages={})

    fake_graph = FakeSegGraph()
    monkeypatch.setattr("app.workflows.segmentation.segmentation_worker.SEG_GRAPH", fake_graph)

    worker = SegmentationWorker(
        seg_queue=asyncio.Queue(),
        image_repo=page_repo,
        segmentation_service=FakeSegmentationService(),
        storage=storage,
    )

    with pytest.raises(RuntimeError, match="read json failed"):
        await worker.handle(page)

    # nothing else should happen
    assert page_repo.get_calls == []
    assert page_repo.update_calls == []


@pytest.mark.asyncio
async def test_segmentation_page_repo_get_error(monkeypatch):
    page_id = "p400"
    page = PageScanRead(
        id=page_id,
        filename="p.jpg",
        bookScanID="b1",
        page_number=1,
        scanDate=scanDate,
    )

    storage = FakeStorage()
    storage.read_json_values[page_id] = OCRResult(page_id=page_id, full_text="", blocks=[])

    page_repo = FakeImageRepository(get_exc=RuntimeError("repo get failed"))

    fake_graph = FakeSegGraph()
    monkeypatch.setattr("app.workflows.segmentation.segmentation_worker.SEG_GRAPH", fake_graph)

    worker = SegmentationWorker(
        seg_queue=asyncio.Queue(),
        image_repo=page_repo,
        segmentation_service=FakeSegmentationService(),
        storage=storage,
    )

    with pytest.raises(RuntimeError, match="repo get failed"):
        await worker.handle(page)


@pytest.mark.asyncio
async def test_segmentation_graph_error(monkeypatch):
    page_id = "p500"
    page = PageScanRead(
        id=page_id,
        filename="p.jpg",
        bookScanID="b1",
        page_number=1,
        scanDate=scanDate,
    )

    storage = FakeStorage()
    storage.read_json_values[page_id] = OCRResult(page_id=page_id, full_text="", blocks=[])

    page_repo = FakeImageRepository(pages={page_id: page})

    fake_graph = FakeSegGraph(exc=RuntimeError("graph failed"))
    monkeypatch.setattr("app.workflows.segmentation.segmentation_worker.SEG_GRAPH", fake_graph)

    worker = SegmentationWorker(
        seg_queue=asyncio.Queue(),
        image_repo=page_repo,
        segmentation_service=FakeSegmentationService(),
        storage=storage,
    )

    with pytest.raises(RuntimeError, match="graph failed"):
        await worker.handle(page)


@pytest.mark.asyncio
async def test_segmentation_repo_update_error(monkeypatch):
    page_id = "p600"
    page = PageScanRead(
        id=page_id,
        filename="p.jpg",
        bookScanID="b1",
        page_number=1,
        scanDate=scanDate,
    )

    storage = FakeStorage()
    storage.read_json_values[page_id] = OCRResult(page_id=page_id, full_text="", blocks=[])

    page_repo = FakeImageRepository(
        pages={page_id: page},
        update_exc=RuntimeError("repo update failed"),
    )

    seg_segment = SegmentationSegment(
        id=1,
        title="t",
        bounding_boxes=[[{"x": 0, "y": 0}]],
        associated_ocr_blocks=[],
    )

    seg_result = SegmentationResult(
        page_segments=[seg_segment],
        segmentation_done=True,
    )

    fake_graph = FakeSegGraph(
        result={
            "__interrupt__": True,
            "segmentation": seg_result,
        }
    )
    monkeypatch.setattr("app.workflows.segmentation.segmentation_worker.SEG_GRAPH", fake_graph)

    worker = SegmentationWorker(
        seg_queue=asyncio.Queue(),
        image_repo=page_repo,
        segmentation_service=FakeSegmentationService(),
        storage=storage,
    )

    with pytest.raises(RuntimeError, match="repo update failed"):
        await worker.handle(page)

    # get and graph should have been executed
    assert page_repo.get_calls == [page_id]
    assert len(fake_graph.calls) == 1

    # but update fails and no broadcast
    assert page_repo.update_calls != []

import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.schemas.ocr import (
    ClassificationRecordCreate,
    ClassificationRecordInputPage,
    ClassificationRecordRead,
    ClassificationRecordUpdate,
    PageScanRead,
    PageType,
    RecordStatus,
    SegmentationSegment,
)
from app.workflows.classification.classification_worker import (
    ClassificationWorker,
    MotifType,
    infer_global_motif,
)
from app.workflows.queues.queues import ClassificationJob

#
# -----------------------------
#   Helper fakes & factories
# -----------------------------
#


class FakeClassificationRepo:
    def __init__(self):
        self.saved = []
        self.updated = []
        self.to_return_get_all = []
        self.owner = None

    async def save(self, record: ClassificationRecordCreate, owner_id: str):
        self.saved.append((record, owner_id))
        return ClassificationRecordRead(
            id="rec-1",
            book_scan_id=record.book_scan_id,
            text_pages=[],
            image_pages=[],
            status=RecordStatus.QUEUED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    async def update(self, update_dto: ClassificationRecordUpdate, owner_id: str = None):
        self.updated.append((update_dto, owner_id))
        return update_dto

    async def get_all_by_book_id(self, book_id: str, owner_id: str):
        return self.to_return_get_all


class FakeGraph:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []

    async def ainvoke(self, state, config):
        self.calls.append((state, config))
        if self.exc:
            raise self.exc
        return self.result


class FakeStorage:
    pass


class FakeValidation:
    pass


class FakeClassService:
    pass


class FakeThumbnail:
    pass


class FakePageRepo:
    pass


class FakeRecipeRepo:
    async def add(self, recipe, owner_id):
        return SimpleNamespace(id="recipe-1")


#
# -----------------------------
#   Page factory
# -----------------------------
#


def make_page(pid: str, page_type: PageType, page_number: int = 1, **kwargs):
    page = PageScanRead(
        id=pid,
        filename=f"{pid}.jpg",
        bookScanID="book-1",
        page_number=page_number,
        scanDate=datetime.now(),
        page_type=page_type,
        page_segments=kwargs.get("page_segments", None),
        segmentation_done=kwargs.get("segmentation_done", False),
        ocr_path=kwargs.get("ocr_path", None),
    )

    # Default for TEXT pages = has a blank block
    if page_type == PageType.TEXT and page.page_segments is None:
        page.page_segments = [SimpleNamespace(title="")]
    elif page.page_segments is None:
        page.page_segments = []

    return page


#
# -----------------------------
#   infer_global_motif tests
# -----------------------------
#


def test_infer_global_motif_empty():
    assert infer_global_motif([]) == MotifType.UNDECIDED


def test_infer_global_motif_single_text():
    assert infer_global_motif([make_page("p1", PageType.TEXT)]) == MotifType.TEXT_IMG


def test_infer_global_motif_single_image():
    assert infer_global_motif([make_page("p1", PageType.IMAGE)]) == MotifType.TEXT_IMG


def test_infer_global_motif_img_text():
    pages = [
        make_page("p1", PageType.IMAGE),
        make_page("p2", PageType.TEXT),
        make_page("p3", PageType.IMAGE),
        make_page("p4", PageType.TEXT),
    ]
    assert infer_global_motif(pages) == MotifType.IMG_TEXT


def test_infer_global_motif_text_img():
    pages = [
        make_page("p1", PageType.TEXT),
        make_page("p2", PageType.IMAGE),
        make_page("p3", PageType.TEXT),
        make_page("p4", PageType.IMAGE),
    ]
    assert infer_global_motif(pages) == MotifType.TEXT_IMG


def test_infer_global_motif_equal_counts_first_image():
    pages = [
        make_page("p1", PageType.IMAGE),
        make_page("p2", PageType.TEXT),
        make_page("p3", PageType.TEXT),
        make_page("p4", PageType.IMAGE),
    ]
    assert infer_global_motif(pages) == MotifType.IMG_TEXT


def test_infer_global_motif_equal_counts_first_text():
    pages = [
        make_page("p1", PageType.TEXT),
        make_page("p2", PageType.IMAGE),
        make_page("p3", PageType.IMAGE),
        make_page("p4", PageType.TEXT),
    ]
    assert infer_global_motif(pages) == MotifType.TEXT_IMG


#
# -----------------------------
#   collect_used_pages_for_book
# -----------------------------
#


@pytest.mark.asyncio
async def test_collect_used_pages_for_book():
    repo = FakeClassificationRepo()
    repo.to_return_get_all = [
        SimpleNamespace(
            text_pages=[SimpleNamespace(id="t1"), SimpleNamespace(id="t2")],
            image_pages=[SimpleNamespace(id="i1")],
        ),
        SimpleNamespace(
            text_pages=[SimpleNamespace(id="t2")],  # duplicate
            image_pages=[SimpleNamespace(id="i3")],
        ),
    ]
    worker = ClassificationWorker(
        class_queue=asyncio.Queue(),
        image_repo=FakePageRepo(),
        classification_service=FakeClassService(),
        validation_service=FakeValidation(),
        thumbnail_service=FakeThumbnail(),
        storage=FakeStorage(),
        classification_repo=repo,
        recipe_repo=FakeRecipeRepo(),
    )

    used = await worker.collect_used_pages_for_book("book-1", owner_id="user1")
    assert used == {"t1", "t2", "i1", "i3"}


#
# -----------------------------
#   group_pages tests
# -----------------------------
#


@pytest.mark.asyncio
async def test_group_pages_img_text_basic():
    pages = [
        make_page("p1", PageType.IMAGE, page_number=1),
        make_page("p2", PageType.TEXT, page_number=2),
        make_page("p3", PageType.IMAGE, page_number=3),
        make_page("p4", PageType.TEXT, page_number=4),
    ]
    groups = ClassificationWorker.group_pages(pages, MotifType.IMG_TEXT, used_pages=set())
    assert len(groups) == 2
    assert all(isinstance(i, ClassificationRecordInputPage) for g in groups for i in g)


@pytest.mark.asyncio
async def test_group_pages_skips_used():
    pages = [
        make_page("p1", PageType.IMAGE),
        make_page("p2", PageType.TEXT),
        make_page("p3", PageType.IMAGE),
    ]
    groups = ClassificationWorker.group_pages(pages, MotifType.IMG_TEXT, used_pages={"p2"})
    # p2 skipped → yields two IMAGE-only groups
    assert len(groups) == 2
    assert all(p.original_id != "p2" for g in groups for p in g)


@pytest.mark.asyncio
async def test_group_pages_text_img_basic():
    pages = [
        make_page("p1", PageType.TEXT),
        make_page("p2", PageType.IMAGE),
        make_page("p3", PageType.TEXT),
        make_page("p4", PageType.IMAGE),
    ]
    groups = ClassificationWorker.group_pages(pages, MotifType.TEXT_IMG, used_pages=set())
    assert len(groups) == 2


#
# -----------------------------
# run_classification_graph
# -----------------------------
#


@pytest.mark.asyncio
async def test_run_classification_graph_interrupt(monkeypatch):
    repo = FakeClassificationRepo()
    graph = FakeGraph(
        result={"__interrupt__": True, "current_recipe_state": SimpleNamespace(), "thumbnail_path": "thumb"}
    )

    # Patch global CLASS_GRAPH in worker module
    monkeypatch.setattr("app.workflows.classification.classification_worker.CLASS_GRAPH", graph)

    worker = ClassificationWorker(
        class_queue=asyncio.Queue(),
        image_repo=FakePageRepo(),
        classification_service=FakeClassService(),
        validation_service=FakeValidation(),
        thumbnail_service=FakeThumbnail(),
        storage=FakeStorage(),
        classification_repo=repo,
        recipe_repo=FakeRecipeRepo(),
    )

    pages = [ClassificationRecordInputPage(original_id="p1", page_number=1, page_type=PageType.TEXT)]
    await worker.run_classification_graph("book-1", pages, owner_id="u1")

    # Graph invoked
    assert len(graph.calls) == 1

    # Repo updated once due to interrupt
    assert len(repo.updated) == 1
    update_dto, owner = repo.updated[0]
    assert update_dto.status == RecordStatus.REVIEW_GROUPING


@pytest.mark.asyncio
async def test_run_classification_graph_no_interrupt(monkeypatch):
    repo = FakeClassificationRepo()
    graph = FakeGraph(result={"done": True})

    monkeypatch.setattr("app.workflows.classification.classification_worker.CLASS_GRAPH", graph)

    worker = ClassificationWorker(
        class_queue=asyncio.Queue(),
        image_repo=FakePageRepo(),
        classification_service=FakeClassService(),
        validation_service=FakeValidation(),
        thumbnail_service=FakeThumbnail(),
        storage=FakeStorage(),
        classification_repo=repo,
        recipe_repo=FakeRecipeRepo(),
    )

    pages = [ClassificationRecordInputPage(original_id="p1", page_number=1, page_type=PageType.TEXT)]
    await worker.run_classification_graph("book-1", pages, owner_id="u1")

    # Graph invoked
    assert len(graph.calls) == 1

    # No repo update because no interrupt
    assert repo.updated == []


#
# -----------------------------
# handle(job)
# -----------------------------
#


@pytest.mark.asyncio
async def test_handle_no_pages():
    repo = FakeClassificationRepo()
    worker = ClassificationWorker(
        class_queue=asyncio.Queue(),
        image_repo=FakePageRepo(),
        classification_service=FakeClassService(),
        validation_service=FakeValidation(),
        thumbnail_service=FakeThumbnail(),
        storage=FakeStorage(),
        classification_repo=repo,
        recipe_repo=FakeRecipeRepo(),
    )

    job = ClassificationJob(owner_id="u1", pages=[])
    result = await worker.handle(job)
    assert result is None  # Early return


@pytest.mark.asyncio
async def test_handle_calls_run_for_each_group(monkeypatch):
    worker = ClassificationWorker(
        class_queue=asyncio.Queue(),
        image_repo=FakePageRepo(),
        classification_service=FakeClassService(),
        validation_service=FakeValidation(),
        thumbnail_service=FakeThumbnail(),
        storage=FakeStorage(),
        classification_repo=FakeClassificationRepo(),
        recipe_repo=FakeRecipeRepo(),
    )

    pages = [
        make_page("p1", PageType.IMAGE),
        make_page("p2", PageType.TEXT),
        make_page("p3", PageType.IMAGE),
        make_page("p4", PageType.TEXT),
    ]

    calls = []

    async def fake_run(**kwargs):
        calls.append(kwargs["input_pages"])

    monkeypatch.setattr(worker, "run_classification_graph", fake_run)

    await worker.handle(ClassificationJob(owner_id="u1", pages=pages))

    assert len(calls) == 2  # 2 groups


@pytest.mark.asyncio
async def test_group_pages_segmented_page_creates_multiple_groups():
    # Fake segments
    seg_prev = SegmentationSegment(
        id=1,
        title="previous_page",
        bounding_boxes=[[{"x": 0, "y": 0}]],
        associated_ocr_blocks=[],
    )
    seg_new = SegmentationSegment(
        id=1,
        title="New Recipe Title",
        bounding_boxes=[[{"x": 0, "y": 0}]],
        associated_ocr_blocks=[],
    )

    page = make_page(
        "p1",
        PageType.TEXT,
        page_number=1,
        segmentation_done=True,
        page_segments=[seg_prev, seg_new],
        ocr_path="ocr.json",
    )

    groups = ClassificationWorker.group_pages([page], MotifType.TEXT_IMG, used_pages=set())

    # Expected:
    # group1 = segment_prev
    # group2 = segment_new
    assert len(groups) == 2
    assert all(isinstance(p, ClassificationRecordInputPage) for g in groups for p in g)

    assert groups[0][0].relevant_segment.title == "previous_page"
    assert groups[1][0].relevant_segment.title == "New Recipe Title"


@pytest.mark.asyncio
async def test_group_pages_text_starts_new_group_under_text_img():
    p1 = make_page("p1", PageType.TEXT, page_number=1)
    p2 = make_page("p2", PageType.TEXT, page_number=2)

    groups = ClassificationWorker.group_pages([p1, p2], MotifType.TEXT_IMG, used_pages=set())

    # TEXT_IMG means every TEXT is a new record
    assert len(groups) == 2
    assert groups[0][0].original_id == "p1"
    assert groups[1][0].original_id == "p2"


@pytest.mark.asyncio
async def test_handle_returns_none_when_no_groups():
    repo = FakeClassificationRepo()
    worker = ClassificationWorker(
        class_queue=asyncio.Queue(),
        image_repo=FakePageRepo(),
        classification_service=FakeClassService(),
        validation_service=FakeValidation(),
        thumbnail_service=FakeThumbnail(),
        storage=FakeStorage(),
        classification_repo=repo,
        recipe_repo=FakeRecipeRepo(),
    )

    job = ClassificationJob(owner_id="u1", pages=[])
    assert await worker.handle(job) is None


@pytest.mark.asyncio
async def test_group_pages_text_with_empty_segments_appends():
    p1 = make_page("p1", PageType.IMAGE)
    p2 = make_page("p2", PageType.TEXT, page_segments=[])

    groups = ClassificationWorker.group_pages([p1, p2], MotifType.IMG_TEXT, used_pages=set())

    # Should be one combined group
    assert len(groups) == 2
    assert groups[0][0].original_id == "p1"
    assert groups[1][0].original_id == "p2"


@pytest.mark.asyncio
async def test_group_pages_skips_segmented_pages_if_used():
    seg = SegmentationSegment(
        id=1,
        title="previou_page",
        bounding_boxes=[[{"x": 0, "y": 0}]],
        associated_ocr_blocks=[],
    )
    p1 = make_page(
        "p1",
        PageType.TEXT,
        segmentation_done=True,
        page_segments=[seg],
    )

    groups = ClassificationWorker.group_pages([p1], MotifType.TEXT_IMG, used_pages={"p1"})
    assert groups == []  # entirely skipped


@pytest.mark.asyncio
async def test_group_pages_segment_prev_page_keeps_in_group():
    seg_prev = SegmentationSegment(
        id=1,
        title="previous_page",
        bounding_boxes=[[{"x": 0, "y": 0}]],
        associated_ocr_blocks=[],
    )

    p1 = make_page(
        "p1",
        PageType.TEXT,
        segmentation_done=True,
        page_segments=[seg_prev],
    )
    p2 = make_page(
        "p2",
        PageType.TEXT,
        segmentation_done=True,
        page_segments=[seg_prev],
    )

    groups = ClassificationWorker.group_pages([p1, p2], MotifType.TEXT_IMG, used_pages=set())

    # Should be one group because both are previous_page segments
    assert len(groups) == 1
    assert len(groups[0]) == 2

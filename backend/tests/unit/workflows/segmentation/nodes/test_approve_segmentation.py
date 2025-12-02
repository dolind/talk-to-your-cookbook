import pytest
from unit.workflows.segmentation.nodes.fakes import FakeBroadcast, FakeRepo

from app.schemas.ocr import (
    OCRResult,
    PageScanUpdate,
    PageStatus,
    SegmentationGraphState,
    SegmentationResult,
    SegmentationSegment,
)
from app.workflows.segmentation.nodes.approve_segmentation import approve_segmentation


@pytest.mark.asyncio
async def test_approve_segmentation_happy_path(monkeypatch):
    page_id = "p1"

    seg_segment = SegmentationSegment(
        id=1,
        title="t",
        bounding_boxes=[[{"x": 0, "y": 0}]],
        associated_ocr_blocks=[],
    )
    seg_result = SegmentationResult(
        segmentation_done=True,
        page_segments=[seg_segment],
    )
    state = SegmentationGraphState(
        page_record_id=page_id,
        segmentation=seg_result,
        ocr_result=OCRResult(page_id=page_id, full_text="hi", blocks=[]),
    )

    fake_repo = FakeRepo()
    fake_broadcast = FakeBroadcast()

    monkeypatch.setattr(
        "app.workflows.segmentation.nodes.approve_segmentation.broadcast_status",
        fake_broadcast,
    )

    out = await approve_segmentation(state, {"configurable": {"page_repo": fake_repo}})

    # repo called
    assert len(fake_repo.update_calls) == 1
    dto: PageScanUpdate = fake_repo.update_calls[0]

    assert dto.id == page_id
    assert dto.status == PageStatus.APPROVED
    assert dto.page_segments == [seg_segment]
    assert dto.segmentation_done is True

    # broadcast fired
    assert len(fake_broadcast.calls) == 1
    msg = fake_broadcast.calls[0]
    assert msg.id == page_id
    assert msg.status == PageStatus.APPROVED

    # returns {}
    assert out == {}


@pytest.mark.asyncio
async def test_approve_segmentation_repo_error(monkeypatch):
    page_id = "p2"

    seg_segment = SegmentationSegment(
        id=1,
        title="t",
        bounding_boxes=[[{"x": 0, "y": 0}]],
        associated_ocr_blocks=[],
    )
    seg_result = SegmentationResult(
        segmentation_done=True,
        page_segments=[seg_segment],
    )
    state = SegmentationGraphState(
        page_record_id=page_id,
        segmentation=seg_result,
        ocr_result=OCRResult(page_id=page_id, full_text="hi", blocks=[]),
    )

    repo = FakeRepo(update_exc=RuntimeError("db fail"))

    monkeypatch.setattr(
        "app.routes.status.broadcast_status",
        lambda msg: None,
    )

    with pytest.raises(RuntimeError, match="db fail"):
        await approve_segmentation(state, {"configurable": {"page_repo": repo}})

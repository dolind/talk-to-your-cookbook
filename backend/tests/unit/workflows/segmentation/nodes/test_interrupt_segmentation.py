import pytest

from app.schemas.ocr import (
    OCRResult,
    SegmentationApproval,
    SegmentationGraphState,
    SegmentationResult,
    SegmentationSegment,
)
from app.workflows.segmentation.nodes.interrupt_segmentation import interrupt_segmentation


@pytest.mark.asyncio
async def test_interrupt_segmentation_happy_path(monkeypatch):
    # segmentation result to return
    seg_segment = SegmentationSegment(
        id=1,
        title="t",
        bounding_boxes=[[{"x": 0, "y": 0}]],
        associated_ocr_blocks=[],
    )
    approval = SegmentationApproval(
        segmentation=SegmentationResult(
            segmentation_done=True,
            page_segments=[seg_segment],
        )
    )

    fake_interruption_payload = {"response_to_approve_seg": approval}

    # fake the `interrupt()` call
    def fake_interrupt(payload):
        return fake_interruption_payload

    monkeypatch.setattr(
        "app.workflows.segmentation.nodes.interrupt_segmentation.interrupt",
        fake_interrupt,
    )

    state = SegmentationGraphState(page_record_id="p1", ocr_result=OCRResult(page_id="p1", full_text="hi", blocks=[]))
    out = await interrupt_segmentation(state)

    # returned dict must contain a dict (model_dump result)
    assert out["segmentation"]["segmentation_done"] is True
    assert out["segmentation"]["page_segments"][0]["id"] == 1

import pytest
from unit.workflows.segmentation.nodes.fakes import FakeSegmentationService

from app.schemas.ocr import OCRResult, SegmentationGraphState, SegmentationResult
from app.workflows.segmentation.nodes.start_segmentation import start_segmentation


@pytest.mark.asyncio
async def test_start_segmentation_happy_path():
    ocr = OCRResult(page_id="p1", full_text="hi", blocks=[])
    state = SegmentationGraphState(page_record_id="p1", ocr_result=ocr)

    result_obj = SegmentationResult(segmentation_done=True, page_segments=[])
    fake_service = FakeSegmentationService(result=result_obj)

    config = {"configurable": {"segmentation_service": fake_service}}

    out = await start_segmentation(state, config)

    # service called correctly
    assert fake_service.calls == [(ocr, True)]

    # returned correct dict
    assert out == {"segmentation": result_obj}


@pytest.mark.asyncio
async def test_start_segmentation_error():
    ocr = OCRResult(page_id="p1", full_text="hi", blocks=[])
    state = SegmentationGraphState(page_record_id="p1", ocr_result=ocr)

    fake_service = FakeSegmentationService(exc=RuntimeError("seg failed"))

    config = {"configurable": {"segmentation_service": fake_service}}

    with pytest.raises(RuntimeError, match="seg failed"):
        await start_segmentation(state, config)

import pytest

from app.infra.classification_simple import ClassificationSimple
from app.schemas.ocr import OCRResult


@pytest.mark.asyncio
async def test_classify_calls_parser_with_full_text():
    # Fake parser with async parse
    called = {}

    class FakeParser:
        async def parse(self, text):
            called["text"] = text
            return {"parsed": True}

    parser = FakeParser()
    svc = ClassificationSimple(parser)

    ocr_result = OCRResult(page_id="1", blocks=[], full_text="Hello world")

    out = await svc.classify([], ocr_result)

    assert out == {"parsed": True}
    assert called["text"] == "Hello world"  # ensures correct value passed


@pytest.mark.asyncio
async def test_classify_returns_empty_dict_when_no_ocr_result():
    class FakeParser:
        async def parse(self, text):
            raise AssertionError("parse() should NOT be called when ocr_result is None")

    parser = FakeParser()
    svc = ClassificationSimple(parser)

    out = await svc.classify([], None)

    assert out == {}  # expected default

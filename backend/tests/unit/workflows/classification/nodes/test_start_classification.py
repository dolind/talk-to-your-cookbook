import pytest

from app.schemas.ocr import (
    ClassificationGraphState,
    ClassificationRecordInputPage,
    PageType,
)
from app.workflows.classification.nodes.start_classification import start_classification


class FakeStorage:
    def __init__(self, data):
        self.data = data
        self.calls = []

    async def read_json(self, pid):
        self.calls.append(pid)
        return self.data[pid]


class FakeClassifier:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or {"classified": True}

    async def classify(self, blocks, ocr_obj):
        self.calls.append((blocks, ocr_obj))
        return self.result


def make_input_page(pid: str, page_type: PageType, segmentation_done=False):
    return ClassificationRecordInputPage(
        original_id=pid,
        page_number=1,
        page_type=page_type,
        ocr_path=None,
        segmentation_done=segmentation_done,
    )


@pytest.mark.asyncio
async def test_start_classification_skips_non_text_pages():
    # TEXT page: p2
    pages = [
        make_input_page("p1", PageType.IMAGE),
        make_input_page("p2", PageType.TEXT),
        make_input_page("p3", PageType.IMAGE),
    ]

    ocr_json = {
        "p2": {"page_id": "p2", "full_text": "hello", "blocks": [{"id": 1}]},
    }

    storage = FakeStorage(ocr_json)
    classifier = FakeClassifier()

    state = ClassificationGraphState(input_pages=pages)
    config = {"configurable": {"classification_service": classifier, "storage": storage}}

    result = await start_classification(state, config)

    # Only text page read
    assert storage.calls == ["p2"]

    # classify called with 1 block
    assert len(classifier.calls) == 1
    blocks, ocr_obj = classifier.calls[0]
    assert blocks == [{"id": 1}]
    assert ocr_obj.full_text == "hello"
    assert result == {"llm_candidate": classifier.result}


@pytest.mark.asyncio
async def test_start_classification_multiple_text_pages_segmentation_false():
    pages = [
        make_input_page("p1", PageType.TEXT, segmentation_done=False),
        make_input_page("p2", PageType.TEXT, segmentation_done=False),
    ]

    ocr_json = {
        "p1": {"page_id": "p1", "full_text": "A", "blocks": [{"a": 1}]},
        "p2": {"page_id": "p2", "full_text": "B", "blocks": [{"b": 2}]},
    }

    storage = FakeStorage(ocr_json)
    classifier = FakeClassifier()

    state = ClassificationGraphState(input_pages=pages)
    config = {"configurable": {"classification_service": classifier, "storage": storage}}

    result = await start_classification(state, config)

    # Both TEXT pages read
    assert storage.calls == ["p1", "p2"]

    # OCR blocks aggregated
    blocks, ocr_obj = classifier.calls[0]
    assert blocks == [{"a": 1}, {"b": 2}]

    # full text combined
    assert ocr_obj.full_text == "A\n\nB"

    # base_result from first TEXT page
    assert ocr_obj.page_id == "p1"

    assert result == {"llm_candidate": classifier.result}


@pytest.mark.asyncio
async def test_start_classification_segmentation_done_true():
    pages = [
        make_input_page("p1", PageType.TEXT, segmentation_done=True),
    ]

    ocr_json = {
        "p1": {"page_id": "p1", "full_text": "Segmented", "blocks": [{"s": 9}]},
    }

    storage = FakeStorage(ocr_json)
    classifier = FakeClassifier()

    state = ClassificationGraphState(input_pages=pages)
    config = {"configurable": {"classification_service": classifier, "storage": storage}}

    result = await start_classification(state, config)

    assert storage.calls == ["p1"]

    blocks, ocr_obj = classifier.calls[0]
    assert blocks == [{"s": 9}]
    assert ocr_obj.full_text == "Segmented"

    assert result == {"llm_candidate": classifier.result}


@pytest.mark.asyncio
async def test_start_classification_raises_if_no_text_pages():
    """
    If no TEXT pages exist, base_result stays None and code
    will fail at base_result.page_id. This should propagate.
    """
    pages = [
        make_input_page("i1", PageType.IMAGE),
        make_input_page("i2", PageType.IMAGE),
    ]

    storage = FakeStorage({})
    classifier = FakeClassifier()

    state = ClassificationGraphState(input_pages=pages)
    config = {"configurable": {"classification_service": classifier, "storage": storage}}

    with pytest.raises(Exception):
        await start_classification(state, config)


@pytest.mark.asyncio
async def test_start_classification_propagates_storage_error():
    pages = [make_input_page("p1", PageType.TEXT)]

    class FailingStorage(FakeStorage):
        async def read_json(self, page_id):
            raise RuntimeError("Storage error")

    storage = FailingStorage({})
    classifier = FakeClassifier()

    state = ClassificationGraphState(input_pages=pages)
    config = {"configurable": {"classification_service": classifier, "storage": storage}}

    with pytest.raises(RuntimeError):
        await start_classification(state, config)


@pytest.mark.asyncio
async def test_start_classification_propagates_classifier_error():
    pages = [make_input_page("p1", PageType.TEXT)]

    ocr_json = {
        "p1": {"page_id": "p1", "full_text": "X", "blocks": [{"x": 1}]},
    }

    storage = FakeStorage(ocr_json)

    class BadClassifier(FakeClassifier):
        async def classify(self, blocks, ocr_obj):
            raise RuntimeError("Classifier fail")

    classifier = BadClassifier()

    state = ClassificationGraphState(input_pages=pages)
    config = {"configurable": {"classification_service": classifier, "storage": storage}}

    with pytest.raises(RuntimeError):
        await start_classification(state, config)

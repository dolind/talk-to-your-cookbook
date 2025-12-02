import pytest

from app.schemas.ocr import ClassificationGraphState, ClassificationRecordInputPage, PageType
from app.workflows.classification.nodes.thumbnail import thumbnail_node


class FakeStorage:
    def __init__(self):
        self.calls = []

    async def get_image_path(self, pid, kind):
        self.calls.append(("get", pid, kind))
        return f"/path/{pid}.jpg"

    async def save_binary_image(self, data, filename, kind):
        self.calls.append(("save", filename, kind))


class FakeThumb:
    def __init__(self):
        self.calls = []

    async def generate_thumbnail(self, src):
        self.calls.append(src)
        return b"123"


@pytest.mark.asyncio
async def test_thumbnail_node_happy_path():
    pages = [ClassificationRecordInputPage(original_id="p2", page_type=PageType.IMAGE, page_number=2)]
    state = ClassificationGraphState(input_pages=pages)

    st = FakeStorage()
    th = FakeThumb()
    cfg = {"configurable": {"storage": st, "thumbnail_service": th}}

    out = await thumbnail_node(state, cfg)

    assert out["thumbnail_path"] == "p2_thumb.jpg"
    assert ("get", "p2", "scanner") in st.calls


@pytest.mark.asyncio
async def test_thumbnail_node_no_image():
    pages = [ClassificationRecordInputPage(original_id="p1", page_type=PageType.TEXT, page_number=1)]
    state = ClassificationGraphState(input_pages=pages)

    st = FakeStorage()
    th = FakeThumb()
    cfg = {"configurable": {"storage": st, "thumbnail_service": th}}

    out = await thumbnail_node(state, cfg)
    assert out["thumbnail_path"] is None

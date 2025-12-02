import asyncio
from datetime import datetime

import pytest

from app.ports.ocr import OCRService, TextOrImageService
from app.ports.storage import StorageService
from app.schemas.ocr import (
    OCRResult,
    PageScanRead,
    PageScanUpdate,
    PageStatus,
    PageType,
)
from app.workflows.ocr.ocr_worker import OCRWorker


class FakeStorage(StorageService):
    def __init__(self):
        self.image_paths = {}
        self.json_paths = {}

        self.get_image_path_calls = []
        self.save_json_calls = []
        self.get_json_path_calls = []

    async def get_image_path(self, image_id: str, kind: str = "recipe") -> str:
        self.get_image_path_calls.append((image_id, kind))
        return self.image_paths[image_id]

    async def save_json(self, data, path: str):
        self.save_json_calls.append((data, path))

    async def get_json_path(self, image_id: str):
        self.get_json_path_calls.append(image_id)
        return self.json_paths[image_id]

    # ----- Required abstract methods we don’t use -----

    async def save_image(self, *a, **kw):
        raise NotImplementedError()

    async def save_binary_image(self, *a, **kw):
        raise NotImplementedError()

    async def load_image(self, *a, **kw):
        raise NotImplementedError()

    async def delete(self, *a, **kw):
        raise NotImplementedError()

    async def rename(self, *a, **kw):
        raise NotImplementedError()

    async def copy_to_recipe(self, *a, **kw):
        raise NotImplementedError()

    async def read_json(self, *a, **kw):
        raise NotImplementedError()

    def get_file_path(self, *a, **kw):
        raise NotImplementedError()

    async def save_file(self, *a, **kw):
        raise NotImplementedError()


class FakeOCRService(OCRService):
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.extract_calls = []

    async def extract(self, image_path: str, image_id: str):
        self.extract_calls.append((image_path, image_id))
        if self.exc:
            raise self.exc
        return self.result


class FakeImageRepository:
    def __init__(self, dto_to_return: PageScanRead | None = None, exc: Exception | None = None):
        self.dto_to_return = dto_to_return
        self.exc = exc
        self.update_calls: list[PageScanUpdate] = []

    async def update(self, dto: PageScanUpdate) -> PageScanRead:
        self.update_calls.append(dto)
        if self.exc is not None:
            raise self.exc
        return self.dto_to_return


class FakePageClassifier(TextOrImageService):
    def __init__(self, is_text: bool):
        self.is_text = is_text
        self.calls = []

    def is_text_page(self, filename: str) -> bool:
        self.calls.append(filename)
        return self.is_text


# --------- Tests ---------


@pytest.mark.asyncio
async def test_handle_text_page_happy_path(monkeypatch):
    # Queues
    ocr_queue = asyncio.Queue()
    seg_queue = asyncio.Queue()

    image_id = "img123"
    image_path = "/tmp/page1.jpg"
    json_path = "ocr/img123.json"

    scan_date = datetime.now()

    page = PageScanRead(
        id=image_id,
        filename="page1.jpg",
        bookScanID="book1",
        page_number=1,
        scanDate=scan_date,
    )

    ocr_result = OCRResult(page_id=image_id, full_text="Hello World", blocks=[])

    storage = FakeStorage()
    storage.image_paths[image_id] = image_path
    storage.json_paths[image_id] = json_path

    ocr_service = FakeOCRService(result=ocr_result)

    updated_dto = PageScanRead(
        id=image_id,
        filename="page1.jpg",
        bookScanID="book1",
        page_number=1,
        scanDate=scan_date,
        ocr_path=json_path,
        page_type=PageType.TEXT,
        status=PageStatus.OCR_DONE,
    )
    image_repo = FakeImageRepository(dto_to_return=updated_dto)

    classifier = FakePageClassifier(is_text=True)

    # Fake broadcast_status to capture messages
    broadcast_calls = {}

    async def fake_broadcast(message):
        broadcast_calls["message"] = message

    monkeypatch.setattr(
        "app.workflows.ocr.ocr_worker.broadcast_status",
        fake_broadcast,
    )

    worker = OCRWorker(
        ocr_queue=ocr_queue,
        seg_queue=seg_queue,
        image_repo=image_repo,
        ocr_service=ocr_service,
        storage=storage,
        text_or_image=classifier,
    )

    # Act: call handle directly
    await worker.handle(page)

    # Assertions: storage / OCR calls
    assert storage.get_image_path_calls == [(image_id, "scanner")]
    assert classifier.calls == [image_path]
    assert ocr_service.extract_calls == [(image_path, image_id)]

    assert len(storage.save_json_calls) == 1
    saved_data, saved_id = storage.save_json_calls[0]
    assert saved_id == image_id
    assert saved_data == ocr_result.model_dump()

    assert storage.get_json_path_calls == [image_id]

    # Assertions: repo update
    assert len(image_repo.update_calls) == 1
    dto = image_repo.update_calls[0]
    assert dto.id == image_id
    assert dto.status == PageStatus.OCR_DONE
    assert dto.page_type == PageType.TEXT
    assert dto.ocr_path == json_path

    # Assertions: broadcast
    assert "message" in broadcast_calls
    msg = broadcast_calls["message"]
    assert msg.id == image_id
    assert msg.status == PageStatus.OCR_DONE
    assert msg.type == "image"

    # Assertions: segmentation queue receives updated dto
    assert not seg_queue.empty()
    seg_item = seg_queue.get_nowait()
    assert seg_item is updated_dto
    assert seg_item.page_type == PageType.TEXT
    assert seg_item.status == PageStatus.OCR_DONE


@pytest.mark.asyncio
async def test_handle_image_page_skips_ocr_and_json(monkeypatch):
    ocr_queue = asyncio.Queue()
    seg_queue = asyncio.Queue()

    image_id = "img456"
    image_path = "/tmp/page2.jpg"
    scan_date = datetime.now()

    page = PageScanRead(
        id=image_id,
        filename="page2.jpg",
        bookScanID="book2",
        page_number=2,
        scanDate=scan_date,
    )

    storage = FakeStorage()
    storage.image_paths[image_id] = image_path

    ocr_service = FakeOCRService(result=None)  # should not be called

    updated_dto = PageScanRead(
        id=image_id,
        filename="page2.jpg",
        bookScanID="book2",
        page_number=2,
        scanDate=scan_date,
        ocr_path="",
        page_type=PageType.IMAGE,
        status=PageStatus.APPROVED,
    )
    image_repo = FakeImageRepository(dto_to_return=updated_dto)

    classifier = FakePageClassifier(is_text=False)

    broadcast_calls = {}

    async def fake_broadcast(message):
        broadcast_calls["message"] = message

    monkeypatch.setattr(
        "app.workflows.ocr.ocr_worker.broadcast_status",
        fake_broadcast,
    )

    worker = OCRWorker(
        ocr_queue=ocr_queue,
        seg_queue=seg_queue,
        image_repo=image_repo,
        ocr_service=ocr_service,
        storage=storage,
        text_or_image=classifier,
    )

    await worker.handle(page)

    # get_image_path is still required
    assert storage.get_image_path_calls == [(image_id, "scanner")]
    # classifier should be called
    assert classifier.calls == [image_path]

    # OCR and JSON operations must be skipped
    assert ocr_service.extract_calls == []
    assert storage.save_json_calls == []
    assert storage.get_json_path_calls == []

    # Repo update reflects IMAGE + APPROVED + empty ocr_path
    assert len(image_repo.update_calls) == 1
    dto = image_repo.update_calls[0]
    assert dto.id == image_id
    assert dto.page_type == PageType.IMAGE
    assert dto.status == PageStatus.APPROVED
    assert dto.ocr_path == ""

    # Broadcast still happens
    assert "message" in broadcast_calls
    msg = broadcast_calls["message"]
    assert msg.id == image_id
    assert msg.status == PageStatus.APPROVED
    assert msg.type == "image"

    # No item should be sent to segmentation queue for image pages
    assert seg_queue.empty()


@pytest.mark.asyncio
async def test_handle_ocr_error_propagates_and_skips_later_side_effects(monkeypatch):
    """
    If OCR service fails, the exception should propagate and no JSON/save/update/broadcast should occur.
    """
    ocr_queue = asyncio.Queue()
    seg_queue = asyncio.Queue()

    image_id = "img_err_ocr"
    image_path = "/tmp/err_ocr.jpg"
    scan_date = datetime.now()

    page = PageScanRead(
        id=image_id,
        filename="err_ocr.jpg",
        bookScanID="book_err",
        page_number=3,
        scanDate=scan_date,
    )

    storage = FakeStorage()
    storage.image_paths[image_id] = image_path

    ocr_exc = RuntimeError("OCR failed")
    ocr_service = FakeOCRService(result=None, exc=ocr_exc)

    image_repo = FakeImageRepository(dto_to_return=None)
    classifier = FakePageClassifier(is_text=True)

    broadcast_calls = {}

    async def fake_broadcast(message):
        broadcast_calls["message"] = message

    monkeypatch.setattr(
        "app.workflows.ocr.ocr_worker.broadcast_status",
        fake_broadcast,
    )

    worker = OCRWorker(
        ocr_queue=ocr_queue,
        seg_queue=seg_queue,
        image_repo=image_repo,
        ocr_service=ocr_service,
        storage=storage,
        text_or_image=classifier,
    )

    with pytest.raises(RuntimeError) as exc_info:
        await worker.handle(page)

    assert "OCR failed" in str(exc_info.value)

    # get_image_path and classifier are called
    assert storage.get_image_path_calls == [(image_id, "scanner")]
    assert classifier.calls == [image_path]

    # OCR attempted once
    assert ocr_service.extract_calls == [(image_path, image_id)]

    # After OCR failure, nothing else should happen
    assert storage.save_json_calls == []
    assert storage.get_json_path_calls == []
    assert image_repo.update_calls == []
    assert "message" not in broadcast_calls
    assert seg_queue.empty()


@pytest.mark.asyncio
async def test_handle_repo_update_error_propagates_and_skips_broadcast_and_queue(monkeypatch):
    """
    If repository update fails, the exception should propagate, broadcast shouldn't run,
    and nothing should be enqueued to segmentation.
    """
    ocr_queue = asyncio.Queue()
    seg_queue = asyncio.Queue()

    image_id = "img_err_repo"
    image_path = "/tmp/err_repo.jpg"
    json_path = "ocr/err_repo.json"
    scan_date = datetime.now()

    page = PageScanRead(
        id=image_id,
        filename="err_repo.jpg",
        bookScanID="book_err_repo",
        page_number=4,
        scanDate=scan_date,
    )

    ocr_result = OCRResult(page_id=image_id, full_text="Error Repo", blocks=[])

    storage = FakeStorage()
    storage.image_paths[image_id] = image_path
    storage.json_paths[image_id] = json_path

    ocr_service = FakeOCRService(result=ocr_result)

    repo_exc = RuntimeError("DB error")
    image_repo = FakeImageRepository(dto_to_return=None, exc=repo_exc)

    classifier = FakePageClassifier(is_text=True)

    broadcast_calls = {}

    async def fake_broadcast(message):
        broadcast_calls["message"] = message

    monkeypatch.setattr(
        "app.workflows.ocr.ocr_worker.broadcast_status",
        fake_broadcast,
    )

    worker = OCRWorker(
        ocr_queue=ocr_queue,
        seg_queue=seg_queue,
        image_repo=image_repo,
        ocr_service=ocr_service,
        storage=storage,
        text_or_image=classifier,
    )

    with pytest.raises(RuntimeError) as exc_info:
        await worker.handle(page)

    assert "DB error" in str(exc_info.value)

    # Storage + OCR + json path are done before repo failure
    assert storage.get_image_path_calls == [(image_id, "scanner")]
    assert classifier.calls == [image_path]
    assert ocr_service.extract_calls == [(image_path, image_id)]
    assert len(storage.save_json_calls) == 1
    assert storage.get_json_path_calls == [image_id]
    assert len(image_repo.update_calls) == 1

    # But after repo failure, no broadcast and nothing enqueued
    assert "message" not in broadcast_calls
    assert seg_queue.empty()

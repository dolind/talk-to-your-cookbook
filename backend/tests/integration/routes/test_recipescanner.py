import datetime
import io
from unittest.mock import AsyncMock

import pytest

from app.core.deps import (
    get_book_repo,
    get_classification_repo,
    get_current_user,
    get_image_ingest_service,
    get_image_repo,
    get_storage,
)
from app.main import app as fastapi_app
from app.models.ocr import BookScanORM
from app.schemas.ocr import BookScanRead, ClassificationRecordRead, Page, PageScanRead
from app.services.image_ingest_service import ImageIngestService
from app.workflows.queues.queues import ClassificationJob, QueueRegistry, get_queue_registry


@pytest.fixture
def mock_image_service():
    mock = AsyncMock(spec=ImageIngestService)
    mock.ingest_pages.return_value = ["img-abc", "img-def"]
    return mock


@pytest.fixture
def override_image_service(mock_image_service):
    # Apply the override
    fastapi_app.dependency_overrides[get_image_ingest_service] = lambda: mock_image_service
    yield mock_image_service
    # Clean up override safely after test
    fastapi_app.dependency_overrides.pop(get_image_ingest_service, None)


@pytest.mark.asyncio
async def test_get_all_book_scans(authed_client_session, mocker):
    # Mock the repository method
    mock_repo = AsyncMock()
    mock_repo.list_all.return_value = [
        BookScanRead(id="book1", title="Scan A"),
        BookScanRead(id="book2", title="Scan B"),
    ]

    # Patch the dependency to use the mock repo
    fastapi_app.dependency_overrides[get_book_repo] = lambda: mock_repo

    # Perform the request using the authenticated client
    response = await authed_client_session.get("/api/v1/recipescanner/book_scans")

    # Verify
    assert response.status_code == 200
    assert len(response.json()) == 2
    mock_repo.list_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_pages_by_book(authed_client_session, test_user):
    # Mock repositories
    mock_image_repo = AsyncMock()
    mock_book_repo = AsyncMock()

    mock_image_repo.list_by_book.return_value = [
        PageScanRead(
            id="img1",
            page_number=0,
            bookScanID="book123",
            scanDate=datetime.datetime.now(),
            filename="page1.jpg",
        ),
        PageScanRead(
            id="img2",
            page_number=1,
            bookScanID="book123",
            scanDate=datetime.datetime.now(),
            filename="page2.jpg",
        ),
    ]

    mock_book_repo.get_owned.return_value = BookScanRead(id="book123", title="Scan", user_id="user-123")

    # Patch the dependency providers
    fastapi_app.dependency_overrides[get_book_repo] = lambda: mock_book_repo
    fastapi_app.dependency_overrides[get_image_repo] = lambda: mock_image_repo

    # Make the request with your authenticated test user
    resp = await authed_client_session.get("/api/v1/recipescanner/book_scans/book123/pages")

    fastapi_app.dependency_overrides.pop(get_book_repo, None)
    fastapi_app.dependency_overrides.pop(get_image_repo, None)

    # Assertions
    assert resp.status_code == 200
    expected = [
        {
            "id": "img1",
            "page_number": 0,
            "bookScanID": "book123",
            "filename": "page1.jpg",
        },
        {
            "id": "img2",
            "page_number": 1,
            "bookScanID": "book123",
            "filename": "page2.jpg",
        },
    ]

    actual = resp.json()
    for exp, act in zip(expected, actual):
        for key in exp:
            assert act[key] == exp[key]
        datetime.datetime.fromisoformat(act["scanDate"])

    mock_book_repo.get_owned.assert_awaited_once_with("book123", test_user.id)
    mock_image_repo.list_by_book.assert_awaited_once_with("book123", test_user.id)


@pytest.mark.asyncio
async def test_delete_book_scan_if_unlinked(authed_client_session, test_user):
    # Mock the BookScanRepository
    mock_repo = AsyncMock()
    mock_repo.delete_if_unlinked.return_value = True

    # Patch the dependency provider
    fastapi_app.dependency_overrides[get_book_repo] = lambda: mock_repo

    # Perform the DELETE request with authenticated client
    resp = await authed_client_session.delete("/api/v1/recipescanner/book_scans/book123")

    # Assertions
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"]

    # Verify the repo method was called correctly
    mock_repo.delete_if_unlinked.assert_awaited_once_with("book123", test_user.id)


@pytest.mark.asyncio
async def test_delete_book_scan_if_linked_fails(authed_client_session, test_user):
    # Mock the BookScanRepository
    mock_repo = AsyncMock()
    mock_repo.delete_if_unlinked.return_value = False

    # Patch the dependency provider
    fastapi_app.dependency_overrides[get_book_repo] = lambda: mock_repo

    # Perform the DELETE request using the authenticated test client
    resp = await authed_client_session.delete("/api/v1/recipescanner/book_scans/book123")

    # Assertions
    assert resp.status_code == 400
    assert "linked or not found" in resp.json()["detail"]

    # Verify it was called with the right user
    mock_repo.delete_if_unlinked.assert_awaited_once_with("book123", test_user.id)


@pytest.mark.asyncio
async def test_delete_image_success(authed_client_session, test_user):
    # Setup mocks
    mock_repo = AsyncMock()
    mock_storage = AsyncMock()
    mock_book_repo = AsyncMock()

    # Return a valid image and book
    mock_repo.get_owned.return_value = PageScanRead(
        id="img123",
        filename="page1.jpg",
        bookScanID="book1",
        page_number=1,
        scanDate=datetime.datetime.now(),
        ocr_path="ocr/img123.json",
    )
    mock_repo.delete.return_value = None
    mock_book_repo.get_owned.return_value = BookScanRead(id="book1", title="Scan", user_id="user-123")

    # Patch dependency providers
    fastapi_app.dependency_overrides[get_book_repo] = lambda: mock_book_repo
    fastapi_app.dependency_overrides[get_storage] = lambda: mock_storage
    fastapi_app.dependency_overrides[get_image_repo] = lambda: mock_repo

    # Make DELETE request with authenticated test client
    resp = await authed_client_session.delete("/api/v1/recipescanner/images/img123")

    # Assertions
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"]

    mock_repo.get_owned.assert_awaited_once_with("img123", test_user.id)
    mock_repo.delete.assert_awaited_once_with("img123", test_user.id)
    mock_storage.delete.assert_any_await("page1.jpg", "scanner")
    mock_storage.delete.assert_any_await("img123.json", "scanner")


@pytest.mark.asyncio
async def test_approve_segmentation_success(authed_client_session, mocker, test_user):
    # Mock the approve_segments function
    mock_approve_segments = AsyncMock(return_value={"message": "Segmentation for img123 approved."})
    mocker.patch("app.routes.recipescanner.approve_segments", mock_approve_segments)

    # Mock repositories and storage
    mock_image_repo = AsyncMock()
    mock_book_repo = AsyncMock()
    mock_storage = AsyncMock()

    # Return valid entities
    mock_image_repo.get_owned.return_value = PageScanRead(
        id="img123",
        filename="page1.jpg",
        bookScanID="book1",
        page_number=1,
        scanDate=datetime.datetime.now(),
    )
    mock_book_repo.get_owned.return_value = BookScanRead(id="book1", title="Scan", user_id="user-123")

    # Patch dependency providers
    fastapi_app.dependency_overrides[get_book_repo] = lambda: mock_book_repo
    fastapi_app.dependency_overrides[get_storage] = lambda: mock_storage
    fastapi_app.dependency_overrides[get_image_repo] = lambda: mock_image_repo

    # Define the payload
    payload = {
        "segments": [
            {
                "id": "blk1",
                "bounding_box": [0, 0, 10, 10],
                "associated_ocr_blocks": [1, 2],
            }
        ],
        "segmentation_done": True,
        "approved": True,
    }

    # Perform the request via the authenticated test client
    resp = await authed_client_session.post("/api/v1/recipescanner/approve_segmentation/img123", json=payload)

    # ✅ Assertions
    assert resp.status_code == 200
    assert "approved" in resp.json()["message"]

    mock_approve_segments.assert_awaited_once()
    mock_image_repo.get_owned.assert_awaited_once_with("img123", test_user.id)


@pytest.mark.asyncio
async def test_upload_pages_success(override_image_service, authed_client_session, db_session, test_user):
    book = BookScanORM(title="Test Book", user_id=test_user.id)
    db_session.add(book)
    await db_session.commit()

    files = [
        ("files", ("page1.jpg", io.BytesIO(b"fake-image-1"), "image/jpeg")),
        ("files", ("page2.jpg", io.BytesIO(b"fake-image-2"), "image/jpeg")),
    ]

    url = f"/api/v1/recipescanner/upload/{book.id}"

    response = await authed_client_session.post(url, files=files)

    assert response.status_code == 200
    assert response.json() == ["img-abc", "img-def"]

    override_image_service.ingest_pages.assert_awaited_once()
    args, _ = override_image_service.ingest_pages.call_args
    assert args[0] == book.id
    assert len(args[1]) == 2
    assert args[2] == test_user.id


@pytest.mark.asyncio
async def test_add_page_success(authed_client_session, test_user):
    mock_class_repo = AsyncMock()
    mock_image_repo = AsyncMock()

    rec = ClassificationRecordRead(
        id="rec1",
        book_scan_id="b1",
        text_pages=[{"id": "p1", "page_number": 1}],
        image_pages=[],
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
    )
    mock_class_repo.get_owned_by_id.return_value = rec

    mock_image_repo.get_owned.return_value = PageScanRead(
        id="p2", page_number=5, filename="x.jpg", bookScanID="b1", scanDate=datetime.datetime.now()
    )

    mock_class_repo.update.return_value = rec  # return something valid

    fastapi_app.dependency_overrides[get_classification_repo] = lambda: mock_class_repo
    fastapi_app.dependency_overrides[get_image_repo] = lambda: mock_image_repo

    resp = await authed_client_session.post("/api/v1/recipescanner/classification_records/rec1/pages/p2")

    assert resp.status_code == 200
    mock_class_repo.update.assert_awaited_once()
    patch_arg = mock_class_repo.update.call_args[0][0]
    assert patch_arg.text_pages[-1].id == "p2"

    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def with_user(test_user):
    fastapi_app.dependency_overrides[get_current_user] = lambda: test_user
    yield
    fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_add_page_duplicate(authed_client_session, with_user):
    mock_class_repo = AsyncMock()
    mock_image_repo = AsyncMock()

    rec = ClassificationRecordRead(
        id="rec1",
        book_scan_id="b1",
        text_pages=[{"id": "p1", "page_number": 1}],
        image_pages=[],
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
    )
    mock_class_repo.get_owned_by_id.return_value = rec
    mock_image_repo.get_owned.return_value = PageScanRead(
        id="p1", page_number=1, filename="f", bookScanID="b1", scanDate=datetime.datetime.now()
    )

    fastapi_app.dependency_overrides[get_classification_repo] = lambda: mock_class_repo
    fastapi_app.dependency_overrides[get_image_repo] = lambda: mock_image_repo

    resp = await authed_client_session.post("/api/v1/recipescanner/classification_records/rec1/pages/p1")

    assert resp.status_code == 409

    fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_remove_page_success(authed_client_session, with_user):
    mock_repo = AsyncMock()
    mock_image_repo = AsyncMock()

    rec = ClassificationRecordRead(
        id="rec1",
        book_scan_id="b1",
        text_pages=[
            Page(id="p1", page_number=2),
            Page(id="p2", page_number=None),
        ],
        image_pages=[
            Page(id="p3", page_number=1),
        ],
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
    )

    mock_repo.get_owned_by_id.return_value = rec
    mock_image_repo.get_owned.return_value = PageScanRead(
        id="p1", page_number=1, filename="x", bookScanID="b1", scanDate=datetime.datetime.now()
    )

    fastapi_app.dependency_overrides[get_classification_repo] = lambda: mock_repo
    fastapi_app.dependency_overrides[get_image_repo] = lambda: mock_image_repo

    resp = await authed_client_session.delete("/api/v1/recipescanner/classification_records/rec1/pages/p1")

    assert resp.status_code == 200
    mock_repo.update.assert_awaited_once()
    patch_arg = mock_repo.update.call_args[0][0]
    assert len(patch_arg.text_pages) == 1

    fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_remove_page_not_found(authed_client_session, with_user):
    mock_repo = AsyncMock()
    mock_image_repo = AsyncMock()

    rec = ClassificationRecordRead(
        id="rec1",
        book_scan_id="b1",
        text_pages=[{"id": "p1", "page_number": 1}],
        image_pages=[],
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
    )
    mock_repo.get_owned_by_id.return_value = rec
    mock_image_repo.get_owned.return_value = PageScanRead(
        id="p2", page_number=2, filename="x", bookScanID="b1", scanDate=datetime.datetime.now()
    )

    fastapi_app.dependency_overrides[get_classification_repo] = lambda: mock_repo
    fastapi_app.dependency_overrides[get_image_repo] = lambda: mock_image_repo

    resp = await authed_client_session.delete("/api/v1/recipescanner/classification_records/rec1/pages/p2")

    assert resp.status_code == 404

    fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_remove_last_page_deletes_record(authed_client_session, with_user, test_user):
    mock_repo = AsyncMock()
    mock_image_repo = AsyncMock()

    rec = ClassificationRecordRead(
        id="rec1",
        book_scan_id="b1",
        text_pages=[{"id": "p1", "page_number": 1}],
        image_pages=[],
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
    )
    mock_repo.get_owned_by_id.return_value = rec
    mock_image_repo.get_owned.return_value = PageScanRead(
        id="p1", page_number=1, filename="x", bookScanID="b1", scanDate=datetime.datetime.now()
    )

    fastapi_app.dependency_overrides[get_classification_repo] = lambda: mock_repo
    fastapi_app.dependency_overrides[get_image_repo] = lambda: mock_image_repo

    resp = await authed_client_session.delete("/api/v1/recipescanner/classification_records/rec1/pages/p1")

    assert resp.status_code == 200
    mock_repo.delete.assert_awaited_once_with("rec1", owner_id=test_user.id)

    fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trigger_classification_full(
    authed_client_session,
    with_user,
    test_user,
):
    # ----------------------
    # Arrange mocks
    # ----------------------
    mock_class_repo = AsyncMock()
    mock_image_repo = AsyncMock()
    mock_storage = AsyncMock()

    # Simulate queue registry with real asyncio queue
    import asyncio

    cls_q = asyncio.Queue()
    registry = QueueRegistry(ocr=None, seg=None, cls=cls_q, emb=None)

    # record with text + image pages
    rec = ClassificationRecordRead(
        id="rec1",
        book_scan_id="b1",
        recipe_id=None,
        title=None,
        thumbnail_path="thumb.png",
        status="NEEDS_REVIEW",
        approved=False,
        validation_result=None,
        text_pages=[
            Page(id="p1", page_number=2),
            Page(id="p2", page_number=None),
        ],
        image_pages=[
            Page(id="p3", page_number=1),
        ],
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
    )
    mock_class_repo.get_owned_by_id.return_value = rec

    # simulate page lookup in correct sorted order
    mock_image_repo.get_owned.side_effect = [
        PageScanRead(id="p3", page_number=1, filename="p3.jpg", bookScanID="b1", scanDate=datetime.datetime.now()),
        PageScanRead(id="p1", page_number=2, filename="p1.jpg", bookScanID="b1", scanDate=datetime.datetime.now()),
        None,  # p2 should be skipped (None returned)
    ]

    fastapi_app.dependency_overrides[get_classification_repo] = lambda: mock_class_repo
    fastapi_app.dependency_overrides[get_image_repo] = lambda: mock_image_repo
    fastapi_app.dependency_overrides[get_storage] = lambda: mock_storage
    fastapi_app.dependency_overrides[get_queue_registry] = lambda: registry

    # ----------------------
    # Act
    # ----------------------
    resp = await authed_client_session.post("/api/v1/recipescanner/trigger_classification/rec1")

    # ----------------------
    # Assert
    # ----------------------
    assert resp.status_code == 200
    assert "Re-classification triggered" in resp.json()["message"]

    # record fetched
    mock_class_repo.get_owned_by_id.assert_awaited_once_with("rec1", test_user.id)

    # thumbnail deleted
    mock_storage.delete.assert_awaited_once_with("thumb.png", "scanner")

    # record deleted
    mock_class_repo.delete.assert_awaited_once_with("rec1", owner_id=test_user.id)

    # queue got job with expected pages order [p3, p1]
    job: ClassificationJob = await cls_q.get()
    assert len(job.pages) == 2
    assert job.pages[0].id == "p3"
    assert job.pages[1].id == "p1"
    assert job.owner_id == test_user.id

    fastapi_app.dependency_overrides.clear()

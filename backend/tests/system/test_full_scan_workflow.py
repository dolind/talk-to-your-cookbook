import asyncio
import logging
import os

import pytest
from httpx import AsyncClient
from tests.conftest import get_test_file

from app.schemas.ocr import PageScanRead, PageStatus, PageType, RecordStatus

POLL_INTERVAL = 1
TIMEOUT = 10

logger = logging.getLogger(__name__)


async def wait_until(fn, *, timeout=TIMEOUT, interval=POLL_INTERVAL, description="condition"):
    deadline = asyncio.get_running_loop().time() + timeout
    attempt = 0
    while asyncio.get_running_loop().time() < deadline:
        attempt += 1
        try:
            result = await fn()
        except Exception as e:
            logger.info(f"[wait_until] Attempt {attempt} — exception: {e}")
            result = False

        if result:
            logger.info(f"[wait_until] ✅ Condition met: {description}")
            return

        logger.info(f"[wait_until] ⏳ Waiting for {description}... (attempt {attempt})")
        await asyncio.sleep(interval)

    raise TimeoutError(f"⛔ Timed out waiting for: {description}")


@pytest.mark.skipif("GITHUB_ACTIONS" in os.environ, reason="Skip heavy model test in CI")
@pytest.mark.system
@pytest.mark.asyncio
async def test_full_scan_flow(authed_integration_client: AsyncClient, session_maker, queues, test_user):
    async with session_maker() as session:
        # ---------------------------------------------------
        # (1) Create a book scan
        # ---------------------------------------------------
        r = await authed_integration_client.post("/api/v1/recipescanner/book_scans", json={"title": "Test Scan"})
        r.raise_for_status()
        book_scan = r.json()
        book_scan_id = book_scan["id"]

        # ---------------------------------------------------
        # (2) Upload one text page
        # ---------------------------------------------------
        file_path = get_test_file("storage/pages/text_0.png")

        # Open the file in binary mode

        files = [("files", (file_path.name, open(file_path, "rb"), "image/jpeg"))]
        form_data = {"book_scan_id": book_scan_id}

        r = await authed_integration_client.post(
            url=f"/api/v1/recipescanner/upload/{book_scan_id}", data=form_data, files=files
        )
        r.raise_for_status()
        image_ids = r.json()
        assert image_ids, "upload returned no image ids"
        image_id = image_ids[0]
        await asyncio.wait_for(queues["ocr"].join(), timeout=15)

    # ---------------------------------------------------
    # (3) Wait until OCR detects TEXT page
    # ---------------------------------------------------

    async def page_is_text():
        from app.repos.image_repo import ImageRepository as ImageRepo

        repo = ImageRepo(session)
        img = await repo.get_owned(image_id, test_user.id)
        return img.page_type == PageType.TEXT

    await wait_until(page_is_text, description="OCR detects TEXT page")

    # ---------------------------------------------------
    # (4) Wait until the image requires segmentation approval
    # ---------------------------------------------------
    async def needs_approval():
        # Replace with your real repo call
        from app.repos.image_repo import ImageRepository as ImageRepo

        repo = ImageRepo(session)
        img = await repo.get_owned(image_id, test_user.id)

        return getattr(img, "status", None) == PageStatus.NEEDS_REVIEW

    await wait_until(needs_approval, description="WAITING_FOR_APPROVAL")

    # ---------------------------------------------------
    # (5) Approve segmentation
    # ---------------------------------------------------
    approval_payload = {
        "approved": True,
        "segmentation": {
            "segmentation_done": False,
            "page_segments": [
                {
                    "id": 1,
                    "title": "Some title",
                    "bounding_boxes": [[{"x": 10, "y": 20, "width": 100, "height": 50}]],
                    "associated_ocr_blocks": [0, 1, 2],
                }
            ],
        },
    }

    r = await authed_integration_client.post(
        f"/api/v1/recipescanner/approve_segmentation/{image_id}", json=approval_payload
    )
    r.raise_for_status()

    from app.repos.image_repo import ImageRepository as ImageRepo

    image_repo = ImageRepo(session)
    updated: PageScanRead = await image_repo.get_owned(image_id, test_user.id)

    assert updated.status == PageStatus.APPROVED
    assert updated.page_type == PageType.TEXT

    # ---------------------------------------------------
    # (6) Trigger classification for entire book
    # ---------------------------------------------------
    r = await authed_integration_client.post(url=f"/api/v1/recipescanner/classify_book_scan/{book_scan_id}")
    r.raise_for_status()

    # ---------------------------------------------------
    # (7) Wait for first interrupt (grouping review)
    # ---------------------------------------------------
    async def waiting_for_grouping_review():
        from app.repos.classification_record import ClassificationRecordRepository as RecordRepo

        repo = RecordRepo(session)
        records = await repo.get_all_owned_by_book_id(book_scan_id, test_user.id)
        assert len(records) == 1
        one_record = records[0]
        return getattr(one_record, "status", None) == RecordStatus.REVIEW_GROUPING

    await wait_until(waiting_for_grouping_review, description="grouping REVIEW_GROUPING")

    # ---------------------------------------------------
    # (8) Approve grouping
    # ---------------------------------------------------

    from app.repos.classification_record import ClassificationRecordRepository as RecordRepo

    repo = RecordRepo(session)
    records = await repo.get_all_owned_by_book_id(book_scan_id, test_user.id)

    assert len(records) == 1
    record_id = records[0].id
    approval_payload = {
        "phase": "group",
        "approved": True,  # optional, defaults to True
    }
    r = await authed_integration_client.post(
        f"/api/v1/recipescanner/approve_classification/{record_id}", json=approval_payload
    )

    # ---------------------------------------------------
    # (9) Wait for second interrupt: recipe review (NEEDS_REVIEW)
    # ---------------------------------------------------
    async def waiting_for_recipe_review():
        from app.repos.classification_record import ClassificationRecordRepository as RecordRepo

        repo = RecordRepo(session)
        records = await repo.get_all_owned_by_book_id(book_scan_id, test_user.id)
        one = records[0]
        return getattr(one, "status", None) == RecordStatus.NEEDS_REVIEW

    await wait_until(waiting_for_recipe_review, description="classification NEEDS_REVIEW")

    # ---------------------------------------------------
    # (10) User approves recipe (RecipeApproval)
    # ---------------------------------------------------

    assert len(records) == 1
    record_id = records[0].id
    approval_payload = {
        "phase": "recipe",
        "approved": True,  # optional, defaults to True
    }
    r = await authed_integration_client.post(
        f"/api/v1/recipescanner/approve_classification/{record_id}", json=approval_payload
    )

    # ---------------------------------------------------
    # (11) Wait for taxonomy review (NEEDS_TAXONOMY)
    # ---------------------------------------------------

    async def waiting_for_taxonomy_review():
        from app.repos.classification_record import ClassificationRecordRepository as RecordRepo

        repo = RecordRepo(session)
        records = await repo.get_all_owned_by_book_id(book_scan_id, test_user.id)
        one = records[0]
        return getattr(one, "status", None) == RecordStatus.NEEDS_TAXONOMY

    await wait_until(waiting_for_taxonomy_review, description="taxonomy NEEDS_TAXONOMY")

    # ---------------------------------------------------
    # (12) user confirms/edits categories & tags
    # ---------------------------------------------------
    taxonomy_payload = {
        "approved": True,
        "phase": "taxonomy",
        "categories": ["Dinner", "Vegetarian"],
        "tags": ["roasted", "tahini"],
    }
    # If you use a separate endpoint:
    r = await authed_integration_client.post(
        f"/api/v1/recipescanner/approve_classification/{record_id}", json=taxonomy_payload
    )
    # Or, if you reuse the same endpoint, document the shape you expect (e.g., include a "phase":"taxonomy" flag)
    r.raise_for_status()

    # ---------------------------------------------------
    # 13) Wait for final APPROVED state
    # ---------------------------------------------------
    async def finished():
        from app.repos.classification_record import ClassificationRecordRepository as RecordRepo

        repo = RecordRepo(session)
        records = await repo.get_all_owned_by_book_id(book_scan_id, test_user.id)
        assert len(records) == 1
        one_record = records[0]
        return getattr(one_record, "status", None) == RecordStatus.APPROVED

    await wait_until(finished, description="WAITING_FOR_APPROVAL_RESULT")

    # ---------------------------------------------------
    # 14) Recipe persisted with tags/categories
    # ---------------------------------------------------

    async def recipe_in_repo():
        from app.repos.classification_record import ClassificationRecordRepository as RecordRepo

        repo = RecordRepo(session)
        records = await repo.get_all_owned_by_book_id(book_scan_id, test_user.id)
        assert len(records) == 1
        one_record = records[0]
        recipe_id = one_record.recipe_id

        from app.repos.recipe import RecipeRepository as RecipeRepo

        recipe_repo = RecipeRepo(session)
        recipe_record = await recipe_repo.get(recipe_id, owner_id=test_user.id)
        return getattr(recipe_record, "user_id", None) == test_user.id

    await wait_until(recipe_in_repo, description="WAITING_FOR_RECIPE")

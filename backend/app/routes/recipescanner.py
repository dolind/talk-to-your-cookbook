import logging
from math import inf
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.exc import NoResultFound

from app.core.deps import (
    get_book_repo,
    get_classification_repo,
    get_classification_service,
    get_current_user,
    get_image_ingest_service,
    get_image_repo,
    get_recipe_repo,
    get_storage,
    get_thumbnail_service,
    get_validation_service,
)
from app.models.user import User
from app.schemas.ocr import (
    ApprovalBody,
    BookScanCreate,
    BookScanRead,
    ClassificationRecordRead,
    ClassificationRecordUpdate,
    GroupApproval,
    Page,
    PageScanRead,
    RecipeApproval,
    SegmentationApproval,
    TaxonomyApproval,
)
from app.services.image_ingest_service import ImageIngestService
from app.workflows.classification.resume_graph_execution import resume_classification_graph
from app.workflows.queues.queues import ClassificationJob, QueueRegistry, get_queue_registry
from app.workflows.segmentation.resume_graph_execution import approve_segments

logger = logging.getLogger(__name__)

router = APIRouter()


async def ensure_book_access(book_scan_id: str, owner_id: str, book_repo) -> BookScanRead:
    book = await book_repo.get_owned(book_scan_id, owner_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book scan not found")
    return book


async def ensure_image_access(image_id: str, owner_id: str, image_repo) -> PageScanRead:
    image = await image_repo.get_owned(image_id, owner_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


async def ensure_record_access(record_id: str, owner_id: str, classification_repo):
    try:
        return await classification_repo.get_owned_by_id(record_id, owner_id)
    except NoResultFound as exc:
        raise HTTPException(status_code=404, detail="Classification record not found") from exc


@router.post("/book_scans", response_model=BookScanRead)
async def create_book_scan(
    body: BookScanCreate,
    book_repo=Depends(get_book_repo),
    current_user: User = Depends(get_current_user),
):
    created = await book_repo.save(body, current_user.id)
    if created.id is None:
        raise HTTPException(500, "Failed to create book scan")
    return created


@router.post("/trigger_ocr/{image_id}")
async def trigger_ocr(
    image_id: str,
    image_repo=Depends(get_image_repo),
    book_repo=Depends(get_book_repo),
    queue_reqistry: QueueRegistry = Depends(get_queue_registry),
    current_user: User = Depends(get_current_user),
):
    ocr_queue = queue_reqistry.ocr
    image: PageScanRead = await ensure_image_access(image_id, current_user.id, image_repo)
    await ocr_queue.put(image)
    return {"message": f"OCR triggered for {image_id}"}


@router.post("/trigger_seg/{image_id}")
async def trigger_seg(
    image_id: str,
    image_repo=Depends(get_image_repo),
    book_repo=Depends(get_book_repo),
    queue_reqistry: QueueRegistry = Depends(get_queue_registry),
    current_user: User = Depends(get_current_user),
):
    seg_queue = queue_reqistry.seg
    image: PageScanRead = await ensure_image_access(image_id, current_user.id, image_repo)
    await seg_queue.put(image)
    return {"message": f"Segmentation triggered for {image_id}"}


@router.post("/trigger_classification/{record_id}")
async def trigger_classification(
    record_id: str,
    classification_repo=Depends(get_classification_repo),
    image_repo=Depends(get_image_repo),
    queue_reqistry: QueueRegistry = Depends(get_queue_registry),
    storage=Depends(get_storage),
    book_repo=Depends(get_book_repo),
    current_user: User = Depends(get_current_user),
):
    try:
        # get pages of record
        rec = await ensure_record_access(record_id, current_user.id, classification_repo)

        text_pages = rec.text_pages
        image_pages = rec.image_pages

        # order pages
        finalize_pages = text_pages + image_pages
        finalize_pages = sorted(
            finalize_pages, key=lambda p: (p.page_number is None, p.page_number if p.page_number is not None else inf)
        )

        # get images of pages
        pagescans = []
        for page in finalize_pages:
            img = await image_repo.get_owned(page.id, current_user.id)
            if not img:
                continue
            pagescans.append(img)
        # delete record
        if rec.thumbnail_path:
            await storage.delete(rec.thumbnail_path, "scanner")
        await classification_repo.delete(record_id, owner_id=current_user.id)

        # rerun classification with only these pages
        cls_queue = queue_reqistry.cls

        await cls_queue.put(ClassificationJob(pages=pagescans, owner_id=current_user.id))
    except Exception as e:
        logger.info(e)
    return {"message": f"Re-classification triggered for {record_id}"}


# Upload images to a scan
@router.post("/upload/{book_scan_id}", response_model=List[str])
async def upload_pages(
    book_scan_id: str,
    files: list[UploadFile],
    image_service: ImageIngestService = Depends(get_image_ingest_service),
    book_repo=Depends(get_book_repo),
    current_user: User = Depends(get_current_user),
):
    if not files:
        raise HTTPException(400, "No files uploaded")
    await ensure_book_access(book_scan_id, current_user.id, book_repo)
    page_ids = await image_service.ingest_pages(book_scan_id, files, current_user.id)
    return page_ids


# change page number, page should be deleted before changing
@router.post("/update_page_number/{page_id}")
async def update_page_number(
    page_id: str,
    target_number: int,
    image_repo=Depends(get_image_repo),
    current_user: User = Depends(get_current_user),
):
    await ensure_image_access(page_id, current_user.id, image_repo)
    await image_repo.update_page_number(page_id, target_number)
    return {"message": f"Page number changed to {target_number}"}


# Get all book scans
@router.get("/book_scans", response_model=List[BookScanRead])
async def get_all_book_scans(book_repo=Depends(get_book_repo), current_user: User = Depends(get_current_user)):
    return await book_repo.list_all(current_user.id)


# Get pages of a specific book scan
@router.get("/book_scans/{book_scan_id}/pages", response_model=List[PageScanRead])
async def get_pages_by_book(
    book_scan_id: str,
    image_repo=Depends(get_image_repo),
    book_repo=Depends(get_book_repo),
    current_user: User = Depends(get_current_user),
):
    await ensure_book_access(book_scan_id, current_user.id, book_repo)
    pages = await image_repo.list_by_book(book_scan_id, current_user.id)
    if not pages:
        pages = []
    return pages


# Delete a book scan only if it's unlinked
@router.delete("/book_scans/{book_scan_id}")
async def delete_book_scan_if_unlinked(
    book_scan_id: str,
    book_repo=Depends(get_book_repo),
    current_user: User = Depends(get_current_user),
):
    success = await book_repo.delete_if_unlinked(book_scan_id, current_user.id)
    if not success:
        raise HTTPException(400, f"Book scan {book_scan_id} is either linked or not found")
    return {"message": f"Book scan {book_scan_id} deleted"}


# Delete a single image from the scan
@router.delete("/images/{image_id}")
async def delete_image(
    image_id: str,
    image_repo=Depends(get_image_repo),
    storage=Depends(get_storage),
    book_repo=Depends(get_book_repo),
    current_user: User = Depends(get_current_user),
):
    try:
        image: PageScanRead = await ensure_image_access(image_id, current_user.id, image_repo)
        await storage.delete(image.filename, "scanner")
        if image.ocr_path:
            await storage.delete(image.ocr_path.split("/")[-1], "scanner")

        await image_repo.delete(image_id, current_user.id)

        return {"message": f"Image {image_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# Approve segmentation for an image
@router.post("/approve_segmentation/{image_id}")
async def approve_segmentation(
    image_id: str,
    body: SegmentationApproval,
    image_repo=Depends(get_image_repo),
    storage=Depends(get_storage),
    current_user: User = Depends(get_current_user),
):
    try:
        logger.info(f"Approving segmentation for {image_id}")
        await ensure_image_access(image_id, current_user.id, image_repo)
        result = await approve_segments(image_id, body, image_repo, storage)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
    return result


@router.get("/book_scans/{book_scan_id}/classification_records", response_model=List[ClassificationRecordRead])
async def get_classification_by_book(
    book_scan_id: str,
    classification_repo=Depends(get_classification_repo),
    book_repo=Depends(get_book_repo),
    current_user: User = Depends(get_current_user),
):
    await ensure_book_access(book_scan_id, current_user.id, book_repo)
    records = await classification_repo.get_all_owned_by_book_id(book_scan_id, current_user.id)

    if not records:
        records = []
    return records


@router.post("/classify_book_scan/{book_scan_id}")
async def classify_complete_book_scan(
    book_scan_id: str,
    image_repo=Depends(get_image_repo),
    queue_reqistry: QueueRegistry = Depends(get_queue_registry),
    book_repo=Depends(get_book_repo),
    current_user: User = Depends(get_current_user),
):
    await ensure_book_access(book_scan_id, current_user.id, book_repo)
    pages = await image_repo.list_by_book(book_scan_id, current_user.id)
    classification_queue = queue_reqistry.cls
    await classification_queue.put(ClassificationJob(pages=pages, owner_id=current_user.id))
    return {"message": f"Classification triggered for {book_scan_id}"}


@router.post("/approve_classification/{record_id}")
async def approve_classification(
    record_id: str,
    body: ApprovalBody,
    classification_repo=Depends(get_classification_repo),
    validation_service=Depends(get_validation_service),
    recipe_repo=Depends(get_recipe_repo),
    current_user: User = Depends(get_current_user),
    image_repo=Depends(get_image_repo),
    classification_service=Depends(get_classification_service),
    thumbnail_service=Depends(get_thumbnail_service),
    storage=Depends(get_storage),
    book_repo=Depends(get_book_repo),
):
    owner_id = current_user.id
    logger.info(f"Approving classification for {record_id}, route")
    try:
        rec = await ensure_record_access(record_id, owner_id, classification_repo)
        logger.info(f"found record {rec}")
        if isinstance(body, TaxonomyApproval):
            if getattr(rec, "status", None) not in {"NEEDS_TAXONOMY", "NEEDS_REVIEW"}:
                raise HTTPException(status_code=409, detail="Record not awaiting taxonomy")
        elif isinstance(body, GroupApproval):
            if getattr(rec, "status", None) not in {"REVIEW_GROUPING"}:
                raise HTTPException(status_code=409, detail="Record not awaiting group review")
        elif isinstance(body, RecipeApproval):
            if getattr(rec, "status", None) not in {"NEEDS_REVIEW"}:
                raise HTTPException(status_code=409, detail="Record not awaiting recipe approval")

        await resume_classification_graph(
            record_id,
            body,
            classification_repo,
            validation_service,
            recipe_repo,
            storage,
            class_service=classification_service,
            page_repo=image_repo,
            thumb_service=thumbnail_service,
            book_repo=book_repo,
            owner_id=owner_id,
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/classification_records/{record_id}")
async def delete_record(
    record_id: str,
    classification_repo=Depends(get_classification_repo),
    storage=Depends(get_storage),
    book_repo=Depends(get_book_repo),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Deleting record {record_id}")
    try:
        record: ClassificationRecordRead = await ensure_record_access(record_id, current_user.id, classification_repo)
        logger.info(f"Deleting record {record.thumbnail_path}")
        if record.thumbnail_path:
            await storage.delete(record.thumbnail_path, "scanner")

        await classification_repo.delete(record_id, owner_id=current_user.id)

        return {"message": f"Image {record_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/ocr_data/{image_id}")
async def get_ocr_data(
    image_id: str,
    storage=Depends(get_storage),
    image_repo=Depends(get_image_repo),
    book_repo=Depends(get_book_repo),
    current_user: User = Depends(get_current_user),
):
    await ensure_image_access(image_id, current_user.id, image_repo)
    return await storage.read_json(image_id)


@router.get("/classification_records/{record_id}", response_model=ClassificationRecordRead)
async def get_classification_record(
    record_id: str,
    classification_repo=Depends(get_classification_repo),
    current_user: User = Depends(get_current_user),
    book_repo=Depends(get_book_repo),
):
    record = await ensure_record_access(record_id, current_user.id, classification_repo)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.post("/classification_records/{record_id}/pages/{page_id}", response_model=ClassificationRecordRead)
async def add_page_to_record(
    record_id: str,
    page_id: str,
    classification_repo=Depends(get_classification_repo),
    image_repo=Depends(get_image_repo),
    book_repo=Depends(get_book_repo),
    current_user: User = Depends(get_current_user),
):
    """Add a page (text or image) to an existing classification record."""
    owner_id = current_user.id

    # Ensure both entities exist and are owned
    record = await ensure_record_access(record_id, owner_id, classification_repo)
    page = await ensure_image_access(page_id, owner_id, image_repo)

    # Determine where to add the page

    pages = record.text_pages or []
    if any(p.id == page_id for p in pages):
        raise HTTPException(status_code=409, detail=f"Page {page_id} already in record text pages")
    pages.append(Page(id=page.id, page_number=page.page_number))
    patch = ClassificationRecordUpdate(id=record_id, text_pages=pages)

    # Update record
    updated_record = await classification_repo.update(patch, owner_id=owner_id)
    return updated_record


@router.delete("/classification_records/{record_id}/pages/{page_id}")
async def remove_page_from_record(
    record_id: str,
    page_id: str,
    classification_repo=Depends(get_classification_repo),
    image_repo=Depends(get_image_repo),
    book_repo=Depends(get_book_repo),
    current_user: User = Depends(get_current_user),
):
    """Remove a page (text or image) from an existing classification record."""
    owner_id = current_user.id

    record = await ensure_record_access(record_id, owner_id, classification_repo)
    _ = await ensure_image_access(page_id, owner_id, image_repo)

    text_pages = [p for p in (record.text_pages or []) if p.id != page_id]

    if len(text_pages) == len(record.text_pages or []):
        raise HTTPException(status_code=404, detail=f"Page {page_id} not found in record {record_id}")

    if not text_pages:
        await classification_repo.delete(record_id, owner_id=owner_id)
        return {"message": f"Record {record_id} deleted (no remaining pages)"}

    patch = ClassificationRecordUpdate(id=record_id, text_pages=text_pages)
    await classification_repo.update(patch, owner_id=owner_id)
    return {"message": f"Page {page_id} removed from record {record_id}"}

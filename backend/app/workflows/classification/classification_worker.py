import asyncio
import enum
import logging
from typing import List, Optional

from app.ports.classification import ClassificationService
from app.ports.storage import StorageService
from app.ports.thumbnail import ThumbnailService
from app.ports.validation import ValidationService
from app.repos.classification_record import ClassificationRecordRepository
from app.repos.image_repo import ImageRepository
from app.repos.recipe import RecipeRepository
from app.routes.status import broadcast_status
from app.schemas.ocr import (
    ClassificationGraphState,
    ClassificationRecordCreate,
    ClassificationRecordInputPage,
    ClassificationRecordRead,
    ClassificationRecordUpdate,
    GraphBroadCast,
    Page,
    PageScanRead,
    PageType,
    RecordStatus,
)
from app.workflows.base_worker import BaseWorker
from app.workflows.classification.graph_builder import build_classification_graph
from app.workflows.queues.queues import ClassificationJob

logger = logging.getLogger(__name__)
CLASS_GRAPH = build_classification_graph()


class MotifType(enum.Enum):
    IMG_TEXT = "IMG_TEXT"
    TEXT_IMG = "TEXT_IMG"
    UNDECIDED = "UNDECIDED"


def infer_global_motif(pages: List[PageScanRead]) -> MotifType:
    """Infer whether images or text pages come first globally."""
    if not pages:
        return MotifType.UNDECIDED
    if len(pages) == 1:
        return MotifType.TEXT_IMG

    it = sum(1 for a, b in zip(pages, pages[1:]) if a.page_type == PageType.IMAGE and b.page_type == PageType.TEXT)
    ti = sum(1 for a, b in zip(pages, pages[1:]) if a.page_type == PageType.TEXT and b.page_type == PageType.IMAGE)

    if it == ti:
        first_type = pages[0].page_type
        return MotifType.IMG_TEXT if first_type == PageType.IMAGE else MotifType.TEXT_IMG
    return MotifType.IMG_TEXT if it > ti else MotifType.TEXT_IMG


class ClassificationWorker(BaseWorker[ClassificationJob]):
    def __init__(
        self,
        class_queue: asyncio.Queue[ClassificationJob],
        image_repo: ImageRepository,
        classification_service: ClassificationService,
        validation_service: ValidationService,
        thumbnail_service: ThumbnailService,
        storage: StorageService,
        classification_repo: ClassificationRecordRepository,
        recipe_repo: RecipeRepository,
    ):
        (super().__init__(entry_queue=class_queue),)
        self.class_service = classification_service

        self.page_repo = image_repo
        self.storage = storage
        self.validation = validation_service
        self.thumb_service = thumbnail_service
        self.classification_repo = classification_repo
        self.recipe_repo = recipe_repo

    async def collect_used_pages_for_book(self, book_id: str, owner_id: Optional[str]) -> set[str]:
        """Return IDs of pages already used in existing records."""
        used: set[str] = set()
        records = await self.classification_repo.get_all_by_book_id(book_id, owner_id=owner_id)
        for r in records:
            for p in r.text_pages + r.image_pages:
                used.add(p.id)
        return used

    @staticmethod
    def is_start_of_new_record(motif: MotifType, new_page: PageScanRead, prev_page: Optional[PageScanRead]) -> bool:
        if motif == MotifType.IMG_TEXT:
            return new_page.page_type == PageType.IMAGE
        if motif == MotifType.TEXT_IMG:
            return new_page.page_type == PageType.TEXT
        if prev_page is None:
            return True
        return prev_page.page_type == PageType.IMAGE and new_page.page_type == PageType.TEXT

    @classmethod
    def group_pages(
        cls,
        pages: List[PageScanRead],
        motif: MotifType,
        used_pages: set[str],
    ) -> List[List[ClassificationRecordInputPage]]:
        """Return grouped pages (list of classification input sets)."""
        groups: List[List[ClassificationRecordInputPage]] = []
        current_group: List[ClassificationRecordInputPage] = []
        prev_page: Optional[PageScanRead] = None

        def finalize_group():
            nonlocal current_group
            if current_group:
                groups.append(list(current_group))
                current_group = []

        for page in pages:
            if page.id in used_pages:
                logger.info(f"Skipping page {page.id} (already used).")
                continue

            if page.page_type == PageType.IMAGE:
                input_page = ClassificationRecordInputPage(
                    original_id=page.id,
                    page_number=page.page_number,
                    page_type=PageType.IMAGE,
                )
                if cls.is_start_of_new_record(motif, page, prev_page):
                    finalize_group()
                    current_group = [input_page]
                else:
                    current_group.append(input_page)

            elif page.page_type == PageType.TEXT:
                if not page.segmentation_done:
                    input_page = ClassificationRecordInputPage(
                        original_id=page.id,
                        page_number=page.page_number,
                        page_type=PageType.TEXT,
                        ocr_path=page.ocr_path,
                    )
                    print(len(page.page_segments))
                    if (
                        len(page.page_segments) == 0
                        or (page.page_segments[0].title or "").strip() != "previous_page"
                        and cls.is_start_of_new_record(motif, page, prev_page)
                    ):
                        finalize_group()
                        current_group = [input_page]
                    else:
                        current_group.append(input_page)
                else:
                    # segmented page: handle multiple segments
                    for segment in page.page_segments:
                        input_page = ClassificationRecordInputPage(
                            original_id=page.id,
                            page_number=page.page_number,
                            page_type=PageType.TEXT,
                            ocr_path=page.ocr_path,
                            relevant_segment=segment,
                            segmentation_done=True,
                        )
                        if (segment.title or "").strip() == "previous_page":
                            current_group.append(input_page)
                        else:
                            finalize_group()
                            current_group = [input_page]

            prev_page = page

        finalize_group()
        return [grp for grp in groups if grp]

    async def run_classification_graph(
        self,
        book_scan_id: str,
        input_pages: List[ClassificationRecordInputPage],
        owner_id: str,
    ):
        """Create record, run graph, update repository based on result."""
        record = ClassificationRecordCreate(book_scan_id=book_scan_id)
        saved: ClassificationRecordRead = await self.classification_repo.save(record, owner_id=owner_id)

        state = ClassificationGraphState(
            classification_record_id=saved.id,
            book_scan_id=book_scan_id,
            input_pages=input_pages,
        )

        config = {
            "configurable": {
                "classification_service": self.class_service,
                "validation_service": self.validation,
                "thumbnail_service": self.thumb_service,
                "storage": self.storage,
                "image_repo": self.page_repo,
                "classification_repo": self.classification_repo,
                "recipe_repo": self.recipe_repo,
                "owner_id": owner_id,
                "thread_id": saved.id,
            }
        }

        logger.info(f"Invoking classification graph for record {saved.id}")
        result = await CLASS_GRAPH.ainvoke(state, config=config)

        if result.get("__interrupt__"):
            logger.info(f"Updating record {saved.id} (needs review)")
            updated = ClassificationRecordUpdate(
                id=saved.id,
                status=RecordStatus.REVIEW_GROUPING,
                text_pages=[Page(id=p.original_id, page_number=p.page_number) for p in input_pages],
            )
            await self.classification_repo.update(updated)
            await broadcast_status(GraphBroadCast(type="record", id=saved.id, status=RecordStatus.REVIEW_GROUPING))
        else:
            logger.info(f"Record {saved.id} classified successfully")

    async def handle(self, job: ClassificationJob):
        """Main entrypoint called by the worker queue."""
        pages = job.pages
        owner_id = job.owner_id

        if not pages:
            logger.info("No pages provided, nothing to do.")
            return

        book_id = pages[0].bookScanID
        used_pages = await self.collect_used_pages_for_book(book_id, owner_id=owner_id)
        motif = infer_global_motif(pages)

        logger.info(f"Processing {len(pages)} pages with motif {motif}")

        groups = self.group_pages(pages, motif, used_pages)
        if not groups:
            logger.info("No new groups to classify.")
            return

        logger.info(f"Prepared {len(groups)} group(s) for classification")

        for group in groups:
            await self.run_classification_graph(
                book_scan_id=book_id,
                input_pages=group,
                owner_id=owner_id,
            )

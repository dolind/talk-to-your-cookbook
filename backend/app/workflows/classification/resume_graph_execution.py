import asyncio
import logging
from collections import defaultdict

from langgraph.types import Command

from app.ports.classification import ClassificationService
from app.ports.storage import StorageService
from app.ports.thumbnail import ThumbnailService
from app.ports.validation import ValidationService
from app.repos.book import BookScanRepository
from app.repos.classification_record import ClassificationRecordRepository
from app.repos.image_repo import ImageRepository
from app.repos.recipe import RecipeRepository
from app.routes.status import broadcast_status
from app.schemas.ocr import ClassificationRecordUpdate, GraphBroadCast, GroupApproval, RecipeApproval, RecordStatus
from app.workflows.classification.classification_worker import CLASS_GRAPH

_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

logger = logging.getLogger(__name__)


async def resume_classification_graph(
    record_id: str,
    body: RecipeApproval,
    classification_repo: ClassificationRecordRepository,
    validation_service: ValidationService,
    recipe_repo: RecipeRepository,
    storage: StorageService,
    page_repo: ImageRepository,
    book_repo: BookScanRepository,
    class_service: ClassificationService,
    thumb_service: ThumbnailService,
    owner_id: str,
):
    logger.info(f"Approving classification for {record_id}")
    lock = _locks[record_id]
    async with lock:
        thread_config = {
            "configurable": {
                "classification_repo": classification_repo,
                "validation_service": validation_service,
                "book_repo": book_repo,
                "recipe_repo": recipe_repo,
                "owner_id": owner_id,
                "storage": storage,
                "thread_id": record_id,
                "classification_service": class_service,
                "thumbnail_service": thumb_service,
                "image_repo": page_repo,
            },
        }

        # route by phase
        if isinstance(body, GroupApproval):
            payload = {"response_to_approve_grouping": body}
            phase = "grouping"
        elif isinstance(body, RecipeApproval):
            payload = {"response_to_approve_llm": body}
            phase = "recipe"
        else:
            payload = {"response_to_approve_taxonomy": body}
            phase = "taxonomy"

        logger.info(f"Invoking graph for stage {phase.capitalize()}...")
        result = await CLASS_GRAPH.ainvoke(Command(resume=payload), config=thread_config)
        if "__interrupt__" in result.keys():
            interrupt_data = result["__interrupt__"]
            logger.info(f"Graph interrupted again during {phase} phase: {interrupt_data}")

            # Handle phase-specific interrupts
            if phase == "grouping":
                # After user modified grouping, next step is classification approval
                logger.info(f"Grouping approved — moving record {record_id} to classification stage.")
                updated_record = ClassificationRecordUpdate(
                    id=record_id,
                    status=RecordStatus.NEEDS_REVIEW,
                    validation_result=result["current_recipe_state"],
                    title=result["current_recipe_state"].title,
                    thumbnail_path=result["thumbnail_path"],
                )
                await classification_repo.update(updated_record, owner_id=owner_id)
                await broadcast_status(GraphBroadCast(type="record", id=record_id, status=RecordStatus.NEEDS_REVIEW))

            elif phase == "recipe":
                # After classification step, now needs taxonomy review
                logger.info(f"Classification approved — moving record {record_id} to taxonomy stage.")
                updated_record = ClassificationRecordUpdate(
                    id=record_id,
                    status=RecordStatus.NEEDS_TAXONOMY,
                    title=result["current_recipe_state"].title,
                    validation_result=result["current_recipe_state"],
                )
                await classification_repo.update(updated_record, owner_id=owner_id)
                await broadcast_status(GraphBroadCast(type="record", id=record_id, status=RecordStatus.NEEDS_TAXONOMY))
        else:
            # graph finished last update inside graph as recipe is written
            logger.info(f"Finished Pipeline for {record_id}")

        logger.info(f"Finished graph for stage {phase.capitalize()}.")

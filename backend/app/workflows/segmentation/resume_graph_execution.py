import asyncio
import logging
from collections import defaultdict

from langgraph.types import Command

from app.schemas.ocr import SegmentationApproval
from app.workflows.segmentation.segmentation_worker import SEG_GRAPH

_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
logger = logging.getLogger(__name__)


# TODO: make this part of the worker thread, by adjusting what kind of object the queue takes.
#   the worker then works on intial and on resume tasks, all segmentation work is done by the segmenteation worker
#  this could also not be diffictul if a lot of scans are added, we want to have the approval to have priority, w
#  e would need a priority queue for this to work
async def approve_segments(
    page_id: str,
    segmentation: SegmentationApproval,
    page_repo,
    storage,
):
    logger.info(f"Approving segments for {page_id}")
    lock = _locks[page_id]
    async with lock:
        thread_config = {
            "configurable": {
                "page_repo": page_repo,
                "storage": storage,
                "thread_id": page_id,
            },
        }
        logger.info("Invoking segmentation graph...")
        await SEG_GRAPH.ainvoke(Command(resume={"response_to_approve_seg": segmentation}), config=thread_config)
    return {"message": f"Segmentation for {page_id} approved."}

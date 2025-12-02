import logging

from langgraph.types import interrupt

from app.schemas.ocr import (
    ClassificationGraphPatch,
    ClassificationGraphState,
    ClassificationRecordInputPage,
    GroupApproval,
)

logger = logging.getLogger(__name__)


async def check_grouping(state: ClassificationGraphState, config) -> ClassificationGraphPatch:
    # Pause graph, return payload
    interrupt_result = interrupt({"request_to_approve_grouping": "payload in state"})
    logger.info(interrupt_result)
    user_response: GroupApproval = interrupt_result["response_to_approve_grouping"]

    if not user_response.approved:
        # user rejected — downstream can branch or stop
        return {"current_recipe_state": None}

    # check if new group is different from existing group
    # user_response.new_group must be identical to input_pages
    old_ids = [(p.original_id, p.page_number) for p in state.input_pages]
    new_ids = []
    if user_response.new_group:
        new_ids = [(p.id, p.page_number) for p in user_response.new_group]

    if not new_ids or new_ids == old_ids:
        logger.info("User approved grouping without changes.")
        return ClassificationGraphPatch(input_pages=state.input_pages)

    # Rehydrate: convert Page -> ClassificationRecordInputPage
    logger.info("User modified grouping — rehydrating input_pages.")

    image_repo = config["configurable"]["image_repo"]
    owner_id: str = config["configurable"]["owner_id"]

    # --- Step 1: Start from existing input pages ---
    input_pages = list(state.input_pages or [])

    # --- Step 2: Remove pages that are no longer part of the group ---
    keep_ids = {pid for pid, _ in new_ids}
    input_pages = [p for p in input_pages if p.original_id in keep_ids]

    # --- Step 3: Add any newly introduced pages ---
    existing_ids = {p.original_id for p in input_pages}
    added_ids = [pid for pid, _ in new_ids if pid not in existing_ids]

    if added_ids and image_repo:
        for pid in added_ids:
            try:
                page = await image_repo.get_owned(pid, owner_id)
                if not page:
                    continue
                # Add one input page per new physical page (no segmentation info)
                input_pages.append(
                    ClassificationRecordInputPage(
                        original_id=page.id,
                        page_number=page.page_number,
                        page_type=page.page_type,
                        ocr_path=page.ocr_path,
                        title=getattr(page, "title", None),
                        segmentation_done=getattr(page, "segmentation_done", False),
                    )
                )
                logger.info(f"Added missing page {page.id} to input_pages")
            except Exception as e:
                logger.warning(f"Could not fetch new page {pid}: {e}")

    # --- Step 4: Sort input_pages according to new order ---
    order_index = {pid: idx for idx, (pid, _) in enumerate(new_ids)}
    input_pages.sort(key=lambda p: order_index.get(p.original_id, 9999))

    # Return the updated patch for downstream graph nodes
    return ClassificationGraphPatch(input_pages=input_pages)

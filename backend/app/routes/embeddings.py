from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user, get_recipe_repo
from app.models.user import User
from app.repos.recipe import RecipeRepository
from app.schemas.embeddings import EmbeddingJob
from app.workflows.queues.queues import QueueRegistry, get_queue_registry

router = APIRouter()


@router.post("/{recipe_id}")
async def trigger_embedding(
    recipe_id: str,
    reindex: bool = True,
    targets: list[str] | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    queue_reqistry: QueueRegistry = Depends(get_queue_registry),
):
    # Backward-compatible logic:
    if targets is None:
        parsed_targets = None
    else:
        # targets can be ["a", "b"] or ["a,b"] depending on client
        parsed_targets = []
        for v in targets:
            if v is None:
                continue
            # Allow CSV fallback
            parsed_targets.extend([x.strip() for x in v.split(",") if x.strip()])

        if not parsed_targets:
            parsed_targets = None

    job = EmbeddingJob(
        recipe_id=recipe_id,
        user_id=str(current_user.id),
        reindex=reindex,
        targets=parsed_targets,
    )

    await queue_reqistry.emb.put(job)
    return {"status": "queued", "recipe_id": recipe_id}


@router.post("/reindex/all")
async def reindex_all(
    current_user: User = Depends(get_current_user),
    recipe_repo: RecipeRepository = Depends(get_recipe_repo),
    queue_reqistry: QueueRegistry = Depends(get_queue_registry),
):
    emb_queue = queue_reqistry.emb
    all_recipes = await recipe_repo.get_all_ids(current_user.id)
    jobs = [
        EmbeddingJob(recipe_id=recipe_id, user_id=str(current_user.id), reindex=True, targets=["local_bge"])
        for recipe_id in all_recipes
    ]

    for job in jobs:
        await emb_queue.put(job)

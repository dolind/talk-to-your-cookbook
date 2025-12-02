import pytest
from httpx import AsyncClient

import app.core.deps as deps
from app.main import app as fastapi_app
from app.models.recipe import Recipe
from app.schemas.embeddings import EmbeddingJob
from app.workflows.queues.queues import QueueRegistry


# --------------------------------------------------------------------
# Local fixture: inject queue registry using the global overrides system
# but NOT inside each test
# --------------------------------------------------------------------
@pytest.fixture
def queue_registry_fixture(queues):
    """
    Inject QueueRegistry using the queues fixture.
    Does NOT override anything inside a test — only here.
    """
    registry = QueueRegistry(
        ocr=queues["ocr"],
        seg=queues["seg"],
        cls=queues["cls"],
        emb=queues.setdefault("emb", __import__("asyncio").Queue()),
    )

    fastapi_app.dependency_overrides[deps.get_queue_registry] = lambda: registry

    yield registry

    # cleanup
    fastapi_app.dependency_overrides.pop(deps.get_queue_registry, None)


# --------------------------------------------------------------------
# Tests — use authed_client_session and queues fixture
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_embedding_single_job(
    authed_client_session: AsyncClient,
    queue_registry_fixture: QueueRegistry,
):
    client = authed_client_session
    emb_q = queue_registry_fixture.emb
    assert emb_q.empty()

    resp = await client.post("/api/v1/embeddings/recipe123")
    assert resp.status_code == 200

    job = await emb_q.get()
    assert isinstance(job, EmbeddingJob)
    assert job.recipe_id == "recipe123"
    assert job.user_id  # should be injected from authed_client_session
    assert job.reindex is True
    assert job.targets is None


@pytest.mark.asyncio
async def test_trigger_embedding_custom_targets(
    authed_client_session: AsyncClient,
    queue_registry_fixture: QueueRegistry,
):
    client = authed_client_session
    emb_q = queue_registry_fixture.emb

    resp = await client.post("/api/v1/embeddings/xyz?reindex=false&targets=local_bge")
    assert resp.status_code == 200

    job = await emb_q.get()
    assert job.recipe_id == "xyz"
    assert job.reindex is False
    assert job.targets == ["local_bge"]


# --------------------------------------------------------------------
# Reindex all
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reindex_all_jobs(
    authed_client_session: AsyncClient,
    db_session,
    test_user,
    queue_registry_fixture: QueueRegistry,
):
    client = authed_client_session
    emb_q = queue_registry_fixture.emb

    # Insert some fake recipes
    for rid, title in [("r1", "A"), ("r2", "B"), ("r3", "C")]:
        db_session.add(
            Recipe(
                id=rid,
                user_id=test_user.id,
                title=title,
                prep_time=1,
                cook_time=1,
                servings=1,
            )
        )
    await db_session.commit()

    resp = await client.post("/api/v1/embeddings/reindex/all")
    assert resp.status_code in (200, 204)

    jobs = []
    while not emb_q.empty():
        jobs.append(await emb_q.get())

    assert len(jobs) == 3
    assert {job.recipe_id for job in jobs} == {"r1", "r2", "r3"}

    for job in jobs:
        assert job.reindex is True
        assert job.targets == ["local_bge"]


@pytest.mark.asyncio
async def test_reindex_all_no_recipes(
    authed_client_session: AsyncClient,
    queue_registry_fixture: QueueRegistry,
):
    client = authed_client_session
    emb_q = queue_registry_fixture.emb
    assert emb_q.empty()

    resp = await client.post("/api/v1/embeddings/reindex/all")
    assert resp.status_code in (200, 204)

    assert emb_q.empty()

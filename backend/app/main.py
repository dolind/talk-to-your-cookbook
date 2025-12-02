import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import get_settings
from app.core.deps import (
    get_classification_service,
    get_ocr_service,
    get_segmentation_service,
    get_text_or_image_service,
    get_thumbnail_service,
    get_validation_service,
    make_scoped_repo,
    new_classification_repo,
    new_image_repo,
    new_recipe_repo,
)
from app.database import init_db as dbmod
from app.database.init_db import ensure_schemas_exist
from app.database.init_embedding_db import build_store_registry
from app.database.init_langgraph_db import langgraph_make_saver
from app.infra.embedding_chunker_langchain import RecursiveChunker
from app.infra.embeding_vectorstore_langchain import PGVectorEmbeddingStore
from app.infra.storage_local import LocalStorageService
from app.routes.api import api_router
from app.services.embedding_service import EmbeddingService
from app.workflows.classification.classification_worker import ClassificationWorker
from app.workflows.ocr.ocr_worker import OCRWorker
from app.workflows.queues.queues import QueueRegistry, get_queue_registry
from app.workflows.recipeassistant.chat_graph_definition import build_simple_rag_graph
from app.workflows.recipeassistant.embedding_worker import EmbeddingWorker
from app.workflows.segmentation.segmentation_worker import SegmentationWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(myapp: FastAPI):
    logger.info(f"Starting with {settings.ENV} and database {settings.async_db_url} ")
    if settings.LOCAL_STORAGE_PATH == "":
        logger.error("Define a storage location in you env file.")
        exit(-1)
    else:
        logger.info(f"Using storage location {settings.LOCAL_STORAGE_PATH}")

    # Startup logic
    logger.info("Starting up application...")
    engine = dbmod.async_engine  # always take it from dbmod
    session_maker = dbmod.SessionMaker  # always take it from dbmod

    # test friendly database connections
    async with engine.begin() as conn:
        try:
            if engine.dialect.name == "postgresql":
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            logger.info("Skipping pgvector extension creation")
        await ensure_schemas_exist()
        await conn.run_sync(dbmod.sync_create_tables)

    logger.info("Database initialized")
    myapp.state.engine = engine
    myapp.state.sessionmaker = session_maker
    if not hasattr(myapp.state, "storage"):
        myapp.state.storage = LocalStorageService(base_path=settings.LOCAL_STORAGE_PATH)

    logger.info("Mounting static files...")

    myapp.mount(
        "/recipe_thumbs", StaticFiles(directory=Path(myapp.state.storage.recipe_image_dir)), name="recipe_thumbs"
    )

    myapp.mount(
        "/scanner_images",
        StaticFiles(directory=Path(myapp.state.storage.scanner_image_dir)),
        name="scanner_images",
    )

    image_repo = make_scoped_repo(new_image_repo, session_maker)
    classification_repo = make_scoped_repo(new_classification_repo, session_maker)
    recipe_repository = make_scoped_repo(new_recipe_repo, session_maker)

    ocr_service = get_ocr_service()
    segmentation_service = get_segmentation_service()
    classification_service = get_classification_service()

    validation_service = get_validation_service()

    dep_thumb = myapp.dependency_overrides.get(get_thumbnail_service, get_thumbnail_service)
    thumbnail_service = dep_thumb

    dep = myapp.dependency_overrides.get(get_queue_registry, get_queue_registry)
    queues: QueueRegistry = dep()

    text_or_imgage_service = get_text_or_image_service()
    ocr_worker = OCRWorker(
        ocr_queue=queues.ocr,
        seg_queue=queues.seg,
        image_repo=image_repo,
        storage=myapp.state.storage,
        ocr_service=ocr_service,
        text_or_image=text_or_imgage_service,
    )

    seg_worker = SegmentationWorker(
        seg_queue=queues.seg,
        image_repo=image_repo,
        segmentation_service=segmentation_service,
        storage=myapp.state.storage,
    )
    class_worker = ClassificationWorker(
        class_queue=queues.cls,
        image_repo=image_repo,
        classification_service=classification_service,
        storage=myapp.state.storage,
        thumbnail_service=thumbnail_service,
        validation_service=validation_service,
        classification_repo=classification_repo,
        recipe_repo=recipe_repository,
    )

    # Embedding fiels
    myapp.state.embedding_service = EmbeddingService(
        repo=recipe_repository, chunker=RecursiveChunker(size=800, overlap=100)
    )

    myapp.state.embedding_stores = {k: PGVectorEmbeddingStore(v) for k, v in build_store_registry().items()}

    myapp.state.embedding_active_version = next(
        iter({t.active_version for t in settings.target_config_list.values()}), "v1"
    )

    worker = EmbeddingWorker(
        entry_queue=queues.emb,
        service=myapp.state.embedding_service,
        stores=myapp.state.embedding_stores,
        current_version=myapp.state.embedding_active_version,
    )

    saver = await langgraph_make_saver()
    myapp.state.recipe_assistant_graph = build_simple_rag_graph(saver)

    worker_tasks = [
        asyncio.create_task(ocr_worker.run(), name="ocr"),
        asyncio.create_task(seg_worker.run(), name="seg"),
        asyncio.create_task(class_worker.run(), name="cls"),
        asyncio.create_task(worker.run(), name="embed"),
    ]

    try:
        yield  # the app runs here
    finally:
        # Cancel all running workers
        for task in worker_tasks:
            task.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)

        logger.info("Shutting down application...")
        await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request processing time middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        error_detail = {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"],
        }
        errors.append(error_detail)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
    )


@app.get("/")
async def root():
    return {"message": "Welcome to the Meal Planner API"}

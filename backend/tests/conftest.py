import asyncio
import logging
import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import Depends
from httpx import ASGITransport
from sqlalchemy import StaticPool, delete, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

import app.core.deps as deps
from app.core.config import get_settings
from app.database import init_db as dbmod
from app.database.base import Base
from app.database.init_db import get_db as real_get_db
from app.experimental.classification_mock import MockClassificationService
from app.experimental.ocr_mock_1 import MockOCRService
from app.infra.storage_local import LocalStorageService
from app.main import app as fastapi_app
from app.models.user import User
from app.workflows.queues.queues import QueueRegistry

# TEST DATABASE CONFIG

DATABASE_URL = "sqlite+aiosqlite:///:memory:"
settings = get_settings()


@pytest.fixture(autouse=True, scope="session")
def configure_logging():
    logging.basicConfig(
        level=logging.INFO,  # or INFO
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    for name in [
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "sqlalchemy",
        "testcontainers",
        "asyncpg",
    ]:
        logging.getLogger(name).setLevel(logging.ERROR)
        logging.getLogger("sqlalchemy.engine.Engine").disabled = True


@pytest_asyncio.fixture(scope="session")
async def engine():
    # if db_backend == "sqlite":
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    yield engine
    await engine.dispose()


# FASTAPI OVERRIDE DB


# SETUP/DROP TABLES


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


#


# FIXTURES
@pytest.fixture(scope="session")
def session_maker(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_maker):
    """Compatibility fixture: yields a single session for direct DB access."""
    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def test_user(user_factory):
    return await user_factory()


@pytest_asyncio.fixture(scope="session")
def user_factory(session_maker):
    async def _create_user(email=None):
        async with session_maker() as db_session:
            user = User(id=str(uuid4()), email=email or f"test-{uuid4()}@example.com", hashed_password="fake")
            db_session.add(user)
            await db_session.commit()
            await db_session.refresh(user)
            return user

    return _create_user


@pytest_asyncio.fixture(scope="session")
async def authed_client_session(session_maker, test_user, mock_storage_session):
    """Ultra-fast client (no lifespan, single user, SQLite).
    - Startup/shutdown not called
    - Session-scoped (shared across tests)
    """

    async def override_get_db():
        async with session_maker() as session:
            yield session

    async def override_get_current_user(db: AsyncSession = Depends(override_get_db)):
        # Always make sure the user exists in *this* DB
        db_user = await db.get(User, test_user.id)
        if not db_user:
            db.add(test_user)
            await db.commit()
            db_user = test_user
        return db_user

    fastapi_app.dependency_overrides[deps.get_db] = override_get_db
    fastapi_app.dependency_overrides[deps.get_current_user] = override_get_current_user
    fastapi_app.dependency_overrides[real_get_db] = override_get_db

    fastapi_app.state.storage = mock_storage_session

    transport = ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


# Safe, always tied to the test loop
# we needed this anyway.
@pytest_asyncio.fixture
async def authed_client(db_session):
    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[deps.get_db] = override_get_db

    transport = ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_as_user():
    """
    Context manager to temporarily override get_current_user
    with a specific user.
    Ensures the user exists in the current DB session.
    """

    class AuthContext:
        def __init__(self, user: User):
            self.user = user

        async def __aenter__(self):
            async def override(db: AsyncSession = Depends(deps.get_db)):
                # Always try to re-fetch from DB
                db_user = await db.get(User, self.user.id)
                if not db_user:
                    # Ensure the user is attached to this session
                    db_user = await db.merge(self.user)
                    await db.flush()
                return db_user

            fastapi_app.dependency_overrides[deps.get_current_user] = override
            return self.user

        async def __aexit__(self, exc_type, exc, tb):
            fastapi_app.dependency_overrides.pop(deps.get_current_user, None)

    def _auth_as(user: User):
        return AuthContext(user)

    return _auth_as


@pytest_asyncio.fixture(scope="session")
async def authed_client_hybrid(session_maker, test_user):
    """Session-scoped client with lifespan events (startup/shutdown once).
    - Still fast (one client for the whole suite)
    - More realistic: startup hooks run
    - Shared user
    """

    async def override_get_db():
        async with session_maker() as session:
            yield session

    fastapi_app.dependency_overrides[deps.get_db] = override_get_db
    fastapi_app.dependency_overrides[deps.get_current_user] = lambda: test_user

    transport = ASGITransport(app=fastapi_app)
    async with LifespanManager(fastapi_app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def mock_storage(tmp_path):
    base_path = tmp_path / "storage"
    base_path.mkdir()
    return LocalStorageService(base_path=str(base_path))


@pytest_asyncio.fixture(scope="session")
async def mock_storage_session(tmp_path_factory):
    base_path = tmp_path_factory.mktemp("storage")
    return LocalStorageService(base_path=str(base_path))


@pytest.fixture
def queues():
    return {
        "ocr": asyncio.Queue(),
        "seg": asyncio.Queue(),
        "cls": asyncio.Queue(),
    }


@pytest.fixture(scope="session", autouse=True)
def ensure_static_dir():
    os.makedirs("../../static", exist_ok=True)


# This is needed to correctly run tests from root with poetry, due to uploads directory
@pytest.fixture(scope="session", autouse=True)
def ensure_cwd_is_tests_backend():
    target_dir = Path(__file__).parent.resolve()
    os.chdir(target_dir)


TEST_DATA_DIR = Path(__file__).parent / "data"


def get_test_file(*parts: str) -> Path:
    """Direct access to test files (doesn't involve storage service)."""
    return TEST_DATA_DIR.joinpath(*parts)


## integration fixtures, kept here for convenience


@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("ankane/pgvector:latest") as postgres:
        yield postgres.get_connection_url()  # sync url


@pytest.fixture(scope="session", autouse=True)
def force_mock_services():
    # Force the app to use the lightweight thumbnail service
    settings.THUMBNAIL_TYPE = "mock"
    settings.SEGMENTATION = "mock"
    settings.LLM_API_PROVIDER = "mock"


@pytest_asyncio.fixture
async def authed_integration_client(pg_engine, session_maker, test_user, queues, mock_storage):
    """Full integration client with:
    - Startup/shutdown per test
    - Postgres schema + extensions
    - Authenticated user
    - Local storage + in-memory queues
    """

    # Ensure pgvector extension + schema exist
    async with pg_engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            print("💥 Original DB error:", e.__cause__)
            raise

    # Patch globals the app uses
    dbmod.async_engine = pg_engine
    dbmod.SessionMaker = session_maker
    fastapi_app.state.storage = mock_storage
    fastapi_app.dependency_overrides[deps.get_storage] = lambda: mock_storage
    fastapi_app.dependency_overrides[deps.get_classification_service()] = lambda: MockClassificationService()
    fastapi_app.dependency_overrides[deps.get_ocr_service()] = lambda: MockOCRService(settings.MOCK_RESPONSE_FILE)

    # DB overrides
    async def override_get_db():
        async with session_maker() as session:
            yield session

    fastapi_app.dependency_overrides[deps.get_db] = override_get_db

    # Auth override
    fastapi_app.dependency_overrides[deps.get_current_user] = lambda: test_user

    # Queues
    ocr_q = asyncio.Queue()
    seg_q = asyncio.Queue()
    cls_q = asyncio.Queue()
    emb_q = asyncio.Queue()
    test_registry = QueueRegistry(ocr=ocr_q, seg=seg_q, cls=cls_q, emb=emb_q)

    fastapi_app.dependency_overrides[deps.get_queue_registry] = lambda: test_registry

    # Spin up client with startup/shutdown
    transport = ASGITransport(app=fastapi_app)
    async with LifespanManager(fastapi_app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
        # Make sure pending queue tasks complete
        await asyncio.wait_for(queues["ocr"].join(), timeout=15)

    # Cleanup overrides
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def clean_db(db_session):
    yield
    # delete from all tables in reverse FK order
    for tbl in reversed(Base.metadata.sorted_tables):
        await db_session.execute(delete(tbl))
    await db_session.commit()


@pytest_asyncio.fixture
async def pg_engine(pg_container):
    # Convert sync URL to async one
    async_url = pg_container.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

    engine = create_async_engine(async_url, echo=True)
    yield engine
    await engine.dispose()

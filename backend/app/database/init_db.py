import logging

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.database.base import Base

logger = logging.getLogger(__name__)
settings = get_settings()
# Create async engine based on configuration
async_engine = create_async_engine(
    settings.async_db_url,
    pool_pre_ping=True,
    echo=False,
)


SessionMaker = async_sessionmaker(async_engine, expire_on_commit=False)


async def ensure_schemas_exist():
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS embeddings;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS lg_checkpoints;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS public;"))


@event.listens_for(async_engine.sync_engine, "connect")
def set_search_path_on_connect(dbapi_connection, connection_record):
    """
    This runs for connections created by SQLAlchemy (asyncpg under the hood).
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SET search_path TO embeddings, lg_checkpoints, public;")
    finally:
        cursor.close()


async def get_db():
    async with SessionMaker() as session:
        yield session


def sync_create_tables(sync_connection):
    Base.metadata.create_all(bind=sync_connection)

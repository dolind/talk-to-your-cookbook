import psycopg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import get_settings


async def langgraph_make_saver() -> AsyncPostgresSaver:
    """
    Creates a PostgresSaver whose tables live in the 'pg_checkpoints' schema.
    In contrast to standard approach we use postgres to store conversations.
    """

    conn = await psycopg.AsyncConnection.connect(get_settings().sync_db_url)  # ✅ async conn
    await conn.set_autocommit(True)
    saver = AsyncPostgresSaver(conn=conn)
    await saver.setup()
    return saver

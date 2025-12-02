from logging.config import fileConfig

from alembic import context
from alembic.runtime.migration import MigrationContext
from sqlalchemy import JSON, Column, engine_from_config, pool
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.type_api import TypeEngine

from app.core.config import settings
from app.database.base import Base
from app.models import chat, meal_plan, ocr, recent_recipe, recipe, shopping_list, user

SCHEMAS = {"public", "embeddings", "lg_checkpoints"}


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set DB URL dynamically
sync_url = settings.async_db_url.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", sync_url)
print(">>> Database:", sync_url)
# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def skip_json_vs_jsonb(
    ctx: MigrationContext,
    inspected_column: Column,
    metadata_column: Column,
    inspected_type: TypeEngine,
    metadata_type: TypeEngine,
) -> bool | None:
    json_types = (JSON, JSONB)
    if isinstance(inspected_type, json_types) and isinstance(metadata_type, json_types):
        # treat them as equal → no autogenerate diff
        return False
    # default behaviour (None means “compare normally”)
    return None


def include_object(object, name, type_, reflected, compare_to):
    # Skip certain tables from autogenerate
    ignore_tables = {}
    if type_ == "table" and name in ignore_tables:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=skip_json_vs_jsonb,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # for sch in SCHEMAS:
        #     connection.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{sch}";')
        #
        # connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA embeddings;")

        connection.exec_driver_sql("SET search_path TO public;")

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=skip_json_vs_jsonb,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

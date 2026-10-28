from collections.abc import AsyncIterator, Iterator

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.main import app
from app.models import Base
from app.shared.config import settings
from app.shared.database import get_session

TEST_DATABASE_URL = make_url(settings.database_url).set(database="ledger_test")


def create_test_database() -> None:
    admin_engine = create_engine(
        TEST_DATABASE_URL.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin_engine.connect() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DATABASE_URL.database},
        )
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE_URL.database}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def migrated_database() -> Iterator[None]:
    create_test_database()
    config = Config("alembic.ini")
    config.attributes["configure_logger"] = False
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL.render_as_string(False))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield


@pytest.fixture
async def session_factory(
    migrated_database: None,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    yield async_sessionmaker(engine, expire_on_commit=False)
    table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    if table_names:
        async with engine.begin() as connection:
            await connection.execute(text(f"TRUNCATE {table_names} CASCADE"))
    await engine.dispose()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

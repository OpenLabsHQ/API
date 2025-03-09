import logging
import os
import shutil
from typing import AsyncGenerator, Callable, Generator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from src.app.core.cdktf.stacks.base_stack import AbstractBaseStack
from src.app.core.db.database import Base, async_get_db
from src.app.enums.regions import OpenLabsRegion
from src.app.main import app
from src.app.schemas.template_range_schema import TemplateRangeSchema
from src.app.utils.cdktf_utils import create_cdktf_dir

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def skip_if_env(var: str, reason: str) -> pytest.MarkDecorator:
    """Return a pytest mark to skip tests if the specified environment variable is set.

    Args:
    ----
        var (str): Environment var to check if set.
        reason (str): Reason why test is being skipped.

    Returns:
    -------
        pytest.MarkDecorator: Pytest skip test decorator.

    """
    return pytest.mark.skipif(os.getenv(var) is not None, reason=reason)


@pytest.fixture(scope="session")
def postgres_container() -> Generator[str, None, None]:
    """Get connection string to Postgres container.

    Returns
    -------
        Generator[str, None, None]: Async connection string to postgres database.

    """
    logger.info("Starting Postgres test container...")
    with PostgresContainer("postgres:17") as container:
        container.start()

        raw_url = container.get_connection_url()
        async_url = raw_url.replace("psycopg2", "asyncpg")

        container_up_msg = f"Test container up => {async_url}"
        logger.info(container_up_msg)

        yield async_url

    logger.info("Postgres test container stopped.")


@pytest.fixture(scope="session", autouse=True)
def create_db_schema(postgres_container: str) -> None:
    """Create database schema synchronously (using psycopg2 driver).

    Args:
    ----
        postgres_container (str): Postgres container connection string.

    Returns:
    -------
        None

    """
    sync_url = postgres_container.replace("asyncpg", "psycopg2")

    create_schema_msg = f"Creating schema with sync engine => {sync_url}"
    logger.info(create_schema_msg)

    sync_engine = create_engine(sync_url, echo=False, future=True)

    try:
        Base.metadata.create_all(sync_engine)
        logger.info("All tables created (sync).")
    except SQLAlchemyError as err:
        logger.exception("Error creating tables.")
        raise err
    finally:
        sync_engine.dispose()
        logger.info("Sync engine disposed after schema creation.")


@pytest.fixture(scope="module")
def synthesize_factory(
    request: pytest.FixtureRequest,
) -> Callable[[type[AbstractBaseStack], TemplateRangeSchema, str, OpenLabsRegion], str]:
    """Get factory to generate CDKTF synthesis for different stack classes."""
    from cdktf import Testing

    def _synthesize(
        stack_cls: type[AbstractBaseStack],
        cyber_range: TemplateRangeSchema,
        stack_name: str = "test_range",
        region: OpenLabsRegion = OpenLabsRegion.US_EAST_1,
    ) -> str:
        """Synthesize generic stack using CDKTF testing library."""
        app = Testing.app()
        test_dir = create_cdktf_dir()

        # Register a finalizer to remove the directory after the test module finishes
        request.addfinalizer(lambda: shutil.rmtree(test_dir, ignore_errors=True))

        # Synthesize the stack using the provided stack class
        return str(
            Testing.synth(stack_cls(app, cyber_range, stack_name, test_dir, region))
        )

    return _synthesize


@pytest_asyncio.fixture(scope="function")
async def async_engine(postgres_container: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async database engine for the entire test session.

    Args:
    ----
        postgres_container (str): Postgres container connection string.

    Returns:
    -------
        AsyncGenerator[AsyncEngine, None]: Async database engine.

    """
    engine = create_async_engine(postgres_container, echo=False, future=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(async_engine: AsyncEngine) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async client fixture that overrides the DB dependency with async sessions.

    Args:
    ----
        async_engine (AsyncEngine): Async database engine object.

    Returns:
    -------
        AsyncGenerator[AsyncClient, None]: Async client for interacting with FastAPI.

    """
    # Create the async session factory
    async_session = async_sessionmaker(
        bind=async_engine, expire_on_commit=False, class_=AsyncSession
    )

    # Override the FastAPI dependency to use this session factory
    async def _override_async_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session() as session:
            yield session

    app.dependency_overrides[async_get_db] = _override_async_get_db

    # Use httpx's ASGITransport to run requests against the FastAPI app in-memory
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # Clean up overrides after the test finishes
    app.dependency_overrides.clear()

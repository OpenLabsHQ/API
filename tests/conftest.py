import copy
import logging
import os
import shutil
import uuid
from typing import AsyncGenerator, Callable, Generator

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

import tests.api.v1.config as api_v1_config
from src.app.core.cdktf.ranges.base_range import AbstractBaseRange
from src.app.core.cdktf.ranges.range_factory import RangeFactory
from src.app.core.cdktf.stacks.base_stack import AbstractBaseStack
from src.app.core.config import settings
from src.app.core.db.database import Base, async_get_db
from src.app.enums.regions import OpenLabsRegion
from src.app.main import app
from src.app.schemas.secret_schema import SecretSchema
from src.app.schemas.template_range_schema import TemplateRangeSchema
from src.app.schemas.user_schema import UserID
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


@pytest.fixture(autouse=True)
def create_test_cdktf_dir(request: pytest.FixtureRequest) -> None:
    """Override settings CDKTF dir for testing."""
    settings.CDKTF_DIR = create_cdktf_dir()

    # Register a finalizer to remove the directory after the test module finishes
    request.addfinalizer(lambda: shutil.rmtree(settings.CDKTF_DIR, ignore_errors=True))


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
def synthesize_factory() -> (
    Callable[[type[AbstractBaseStack], TemplateRangeSchema, str, OpenLabsRegion], str]
):
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

        # Synthesize the stack using the provided stack class
        return str(
            Testing.synth(
                stack_cls(app, cyber_range, stack_name, settings.CDKTF_DIR, region)
            )
        )

    return _synthesize


@pytest.fixture(scope="module")
def range_factory() -> Callable[
    [type[AbstractBaseRange], TemplateRangeSchema, OpenLabsRegion],
    AbstractBaseRange,
]:
    """Get factory to generate range object sythesis output."""

    def _range_synthesize(
        range_cls: type[AbstractBaseRange],
        template: TemplateRangeSchema,
        region: OpenLabsRegion = OpenLabsRegion.US_EAST_1,
        state_file: None = None,
    ) -> AbstractBaseRange:
        """Create range object and return synth() output."""
        range_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        secrets = SecretSchema()

        return RangeFactory.create_range(
            id=range_id,
            template=template,
            region=region,
            owner_id=UserID(id=owner_id),
            secrets=secrets,
            state_file=state_file,
        )

    return _range_synthesize


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
async def client(async_engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
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
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # Clean up overrides after the test finishes
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(
    client: AsyncClient,
) -> AsyncGenerator[AsyncClient, None]:
    """Fixture that registers and logs in a test user and returns an authenticated client.

    It uses the provided client fixture to register the user (if not already registered)
    and then logs in to obtain the JWT cookie. A new AsyncClient is created with the
    authentication cookie and returned.
    """
    # Prepare payloads for user registration and login
    user_register_payload = copy.deepcopy(api_v1_config.base_user_register_payload)
    user_login_payload = copy.deepcopy(api_v1_config.base_user_login_payload)

    # Use a fixed test email for authentication
    test_email = "test-auth@ufsit.club"
    user_register_payload["email"] = test_email
    user_login_payload["email"] = test_email

    # Register the user.
    # Note: if the user already exists, you might get a 409 conflict which you can ignore.
    register_response = await client.post(
        f"{api_v1_config.BASE_ROUTE}/auth/register", json=user_register_payload
    )
    if register_response.status_code not in (
        status.HTTP_200_OK,
        status.HTTP_409_CONFLICT,
    ):
        msg = f"User registration failed: {register_response.text}"
        raise Exception(msg)

    # Log in the user to obtain authentication cookies
    login_response = await client.post(
        f"{api_v1_config.BASE_ROUTE}/auth/login", json=user_login_payload
    )
    assert (  # noqa: S101
        login_response.status_code == status.HTTP_200_OK
    ), f"Login failed: {login_response.text}"
    assert (  # noqa: S101
        "token" in login_response.cookies
    ), "JWT token not set in cookies"

    # Create a new authenticated client with the cookies from login
    auth_client = AsyncClient(cookies=login_response.cookies, base_url=client.base_url)
    yield auth_client
    await auth_client.aclose()

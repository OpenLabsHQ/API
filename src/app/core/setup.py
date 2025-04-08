from contextlib import asynccontextmanager
from typing import Any, AsyncContextManager, AsyncGenerator, Callable

import anyio
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, FastAPI

from .config import AppSettings, DatabaseSettings, RedisQueueSettings, settings
from .db.database import Base
from .db.database import async_engine as engine
from .utils import queue


# Function to create database tables
async def create_tables() -> None:
    """Create SQL tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_redis_queue_pool() -> None:
    """Create Redis queue pool."""
    queue.pool = await create_pool(
        RedisSettings(
            host=settings.REDIS_QUEUE_HOST,
            port=settings.REDIS_QUEUE_PORT,
            password=settings.REDIS_QUEUE_PASSWORD,
        )
    )


async def close_redis_queue_pool() -> None:
    """Close Redis queue pool."""
    await queue.pool.aclose()  # type: ignore


async def set_threadpool_tokens(number_of_tokens: int = 100) -> None:
    """Set thread limit."""
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = number_of_tokens


# Lifespan factory to manage app lifecycle events
def lifespan_factory(
    settings: DatabaseSettings | AppSettings | RedisQueueSettings,
    create_tables_on_start: bool = True,
) -> Callable[[FastAPI], AsyncContextManager[Any]]:
    """Create a lifespan async context manager for a FastAPI app."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[Any, None]:
        from asyncio import Event

        initialization_complete = Event()
        app.state.initialization_complete = initialization_complete

        await set_threadpool_tokens()

        try:
            if isinstance(settings, DatabaseSettings) and create_tables_on_start:
                await create_tables()

            if isinstance(settings, RedisQueueSettings):
                await create_redis_queue_pool()

            initialization_complete.set()

            yield

        finally:
            if isinstance(settings, RedisQueueSettings):
                await close_redis_queue_pool()

    return lifespan


# Function to create the FastAPI app
def create_application(
    router: APIRouter,
    settings: DatabaseSettings | AppSettings,
    create_tables_on_start: bool = True,
    **kwargs: Any,  # noqa: ANN401
) -> FastAPI:
    """Create and configure a FastAPI application based on the provided settings.

    This function initializes a FastAPI application and configures it with various settings
    and handlers based on the type of the `settings` object provided.

    Args:
    ----
    router (APIRouter): The APIRouter object containing the routes to be included in the FastAPI application.

    settings: An instance representing the settings for configuring the FastAPI application.
        It determines the configuration applied:

        - AppSettings: Configures basic app metadata like name, description, contact, and license info.
        - DatabaseSettings: Adds event handlers for initializing database tables during startup.

    create_tables_on_start (bool): A flag to indicate whether to create database tables on application startup. Defaults to True.

    **kwargs (Any): Additional keyword arguments passed directly to the FastAPI constructor.

    Returns:
    -------
        FastAPI: A fully configured FastAPI application instance.

    The function configures the FastAPI application with different features and behaviors
    based on the provided settings. It includes setting up database connections, Redis pools
    for caching, queue, and rate limiting, client-side caching, and customizing the API documentation
    based on the environment settings.

    """
    # --- before creating application ---
    if isinstance(settings, AppSettings):
        to_update = {
            "title": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "description": settings.APP_DESCRIPTION,
            "contact": {"name": settings.CONTACT_NAME, "email": settings.CONTACT_EMAIL},
            "license_info": {
                "name": settings.LICENSE_NAME,
                "url": settings.LICENSE_URL,
            },
        }
        kwargs.update(to_update)

    lifespan = lifespan_factory(settings, create_tables_on_start=create_tables_on_start)

    app = FastAPI(lifespan=lifespan, **kwargs)
    app.include_router(router)

    return app

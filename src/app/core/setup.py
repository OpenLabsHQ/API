from contextlib import asynccontextmanager
from typing import Any, AsyncContextManager, AsyncGenerator, Callable

from fastapi import APIRouter, FastAPI

from ..crud.crud_users import create_user, get_user
from ..middlewares.yaml_middleware import add_yaml_middleware_to_router
from ..schemas.user_schema import UserCreateBaseSchema
from ..utils.crypto import (
    encrypt_private_key,
    generate_master_key,
    generate_rsa_key_pair,
)
from .config import AppSettings, DatabaseSettings, settings
from .db.database import Base, async_get_db
from .db.database import async_engine as engine


# Function to create database tables
async def create_tables() -> None:
    """Create SQL tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Function to initialize admin user
async def initialize_admin_user() -> None:
    """Create admin user if it doesn't exist."""
    try:
        async for session in async_get_db():
            # Create a UserCreateBaseSchema with the admin details
            admin_schema = UserCreateBaseSchema(
                email=settings.ADMIN_EMAIL,
                password=settings.ADMIN_PASSWORD,
                name=settings.ADMIN_NAME,
            )

            admin_user = await get_user(session, settings.ADMIN_EMAIL)

            if not admin_user:
                # This will create the user with RSA keys and proper encryption
                await create_user(session, admin_schema, is_admin=True)
            elif admin_user and not admin_user.public_key:
                # If admin user exists but doesn't have encryption keys (legacy migration),
                # generate keys and add them
                private_key_b64, public_key_b64 = generate_rsa_key_pair()

                # Generate master key from password using Argon2
                master_key, key_salt = generate_master_key(settings.ADMIN_PASSWORD)

                # Encrypt the private key with the master key
                encrypted_private_key_b64 = encrypt_private_key(
                    private_key_b64, master_key
                )

                # Update the user with encryption keys
                admin_user.public_key = public_key_b64
                admin_user.encrypted_private_key = encrypted_private_key_b64
                admin_user.key_salt = key_salt

                await session.commit()
    except Exception as e:
        msg = "Failed to create admin user. Check logs for more details."
        raise ValueError(msg) from e


# Lifespan factory to manage app lifecycle events
def lifespan_factory(
    settings: DatabaseSettings | AppSettings,
    create_tables_on_start: bool = True,
) -> Callable[[FastAPI], AsyncContextManager[Any]]:
    """Create a lifespan async context manager for a FastAPI app."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[Any, None]:

        if isinstance(settings, DatabaseSettings) and create_tables_on_start:
            await create_tables()
            await initialize_admin_user()

        yield

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

    add_yaml_middleware_to_router(app, router_path="/api/v1/templates")

    return app

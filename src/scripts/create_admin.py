#!/usr/bin/env python3
import asyncio
import logging
import os
import sys

# Add the parent directory to sys.path to allow relative imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.db.database import Base, async_engine, async_get_db
from app.crud.crud_users import create_user, get_user
from app.schemas.user_schema import UserCreateBaseSchema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables() -> None:
    """Create SQL tables if they don't exist."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def initialize_admin_user() -> None:
    """Initialize database and create admin user if it doesn't exist."""
    try:
        await create_tables()

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
                logger.info("Admin user %s created successfully.", settings.ADMIN_EMAIL)
            else:
                logger.info("Admin user %s already exists.", settings.ADMIN_EMAIL)

            # Only need to process one session
            break

    except Exception as e:
        logger.error("Failed to create admin user: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(initialize_admin_user())

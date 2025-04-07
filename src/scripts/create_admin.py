import asyncio
import logging
import sys

from ..app.core.config import settings
from ..app.core.db.database import managed_async_get_db
from ..app.crud.crud_users import create_user, get_user
from ..app.schemas.user_schema import UserCreateBaseSchema
from .health_check import wait_for_api_ready

logger = logging.getLogger(__name__)


async def initialize_admin_user() -> None:
    """Create admin user if it doesn't exist assuming the DB is already set up."""
    # First wait for the API to be ready
    api_ready = await wait_for_api_ready(max_retries=25, retry_interval=2)
    if not api_ready:
        logger.error("Could not connect to the API. Exiting.")
        sys.exit(1)

    try:
        async with managed_async_get_db() as db:
            # Create a UserCreateBaseSchema with the admin details
            admin_schema = UserCreateBaseSchema(
                email=settings.ADMIN_EMAIL,
                password=settings.ADMIN_PASSWORD,
                name=settings.ADMIN_NAME,
            )

            admin_user = await get_user(db, settings.ADMIN_EMAIL)

            if not admin_user:
                # This will create the user with RSA keys and proper encryption
                await create_user(db, admin_schema, is_admin=True)
                logger.info("Admin user %s created successfully.", settings.ADMIN_EMAIL)
            else:
                logger.info("Admin user %s already exists.", settings.ADMIN_EMAIL)

    except Exception as e:
        logger.error("Failed to create admin user: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(initialize_admin_user())

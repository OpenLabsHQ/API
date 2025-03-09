import logging
import uuid

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from ..models.range_model import RangeModel
from ..schemas.range_schema import RangeID, RangeSchema

# Configure logging
logger = logging.getLogger(__name__)


async def get_range(
    db: AsyncSession, range_id: RangeID, user_id: uuid.UUID | None = None
) -> RangeModel | None:
    """Get range by id (uuid).

    Args:
    ----
        db (Session): Database connection.
        range_id (RangeID): ID of the deployed range.
        user_id (Optional[uuid.UUID]): If provided, only return templates owned by this user.

    Returns:
    -------
        Optional[RangeModel]: Range if it exists in database.

    """
    mapped_range_model = inspect(RangeModel)
    main_columns = [
        getattr(RangeModel, attr.key) for attr in mapped_range_model.column_attrs
    ]

    stmt = (
        select(RangeModel)
        .where(RangeModel.id == range_id.id)
        .options(load_only(*main_columns))
    )

    if user_id:
        stmt = stmt.filter(RangeModel.owner_id == user_id)

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_range(
    db: AsyncSession, range_schema: RangeSchema, owner_id: uuid.UUID
) -> RangeModel:
    """Create a range and add it to the database.

    Args:
    ----
        db (AsyncSession): Database connection.
        range_schema (RangeSchema): Range object.
        owner_id (uuid.UUID): UUID of user deploying range.

    Returns:
    -------
        RangeModel: The newly created range.

    """
    range_model = RangeModel(**range_schema.model_dump(), owner_id=owner_id)
    db.add(range_model)

    await db.commit()

    return range_model


async def delete_range(db: AsyncSession, range_model: RangeModel) -> bool:
    """Delete a range entry.

    Args:
    ----
        db (AsyncSession): Database session.
        range_model (RangeModel): Range to delete.

    Returns:
    -------
        bool: True if successuflly delete. False otherwise.

    """
    try:
        await db.delete(range_model)
        await db.commit()
        return True
    except Exception as e:
        logger.error("Failed to delete range. Error: %s", e)
        return False


async def is_range_owner(
    db: AsyncSession, range_id: RangeID, user_id: uuid.UUID
) -> bool:
    """Check if a user is the owner of a range template.

    Args:
    ----
        db (Session): Database connection.
        range_id (RangeID): ID of the range.
        user_id (uuid.UUID): ID of the user.

    Returns:
    -------
        bool: True if the user is the owner, False otherwise.

    """
    stmt = (
        select(RangeModel)
        .filter(RangeModel.id == range_id.id)
        .filter(RangeModel.owner_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None

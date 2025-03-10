import logging
import uuid

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import load_only, selectinload

from ..models.template_range_model import TemplateRangeModel
from ..models.template_subnet_model import TemplateSubnetModel
from ..models.template_vpc_model import TemplateVPCModel
from ..schemas.template_range_schema import (
    TemplateRangeBaseSchema,
    TemplateRangeID,
    TemplateRangeSchema,
)
from .crud_vpc_templates import create_vpc_template

logger = logging.getLogger(__name__)


async def get_range_template_headers(
    db: AsyncSession, user_id: uuid.UUID | None = None
) -> list[TemplateRangeModel]:
    """Get list of range template headers.

    Args:
    ----
        db (Session): Database connection.
        user_id (Optional[uuid.UUID]): If provided, only return templates owned by this user.

    Returns:
    -------
        list[TemplateRangeModel]: List of range template objects.

    """
    # Dynamically select non-nested columns/attributes
    mapped_range_model = inspect(TemplateRangeModel)
    main_columns = [
        getattr(TemplateRangeModel, attr.key)
        for attr in mapped_range_model.column_attrs
    ]

    stmt = select(TemplateRangeModel).options(load_only(*main_columns))

    if user_id:
        stmt = stmt.filter(TemplateRangeModel.owner_id == user_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_range_template(
    db: AsyncSession, range_id: TemplateRangeID, user_id: uuid.UUID | None = None
) -> TemplateRangeModel | None:
    """Get range template by id (uuid).

    Args:
    ----
        db (Session): Database connection.
        range_id (TemplateRangeID): ID of the range.
        user_id (Optional[uuid.UUID]): If provided, only return templates owned by this user.

    Returns:
    -------
        Optional[OpenLabsRange]: Range template if it exists in database.

    """
    # Eagerly fetch relationships to make single query
    stmt = (
        select(TemplateRangeModel)
        .options(
            selectinload(TemplateRangeModel.vpcs)
            .selectinload(TemplateVPCModel.subnets)
            .selectinload(TemplateSubnetModel.hosts)
        )
        .filter(TemplateRangeModel.id == range_id.id)
    )

    if user_id:
        stmt = stmt.filter(TemplateRangeModel.owner_id == user_id)

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_range_template(
    db: AsyncSession, range_template: TemplateRangeBaseSchema, owner_id: uuid.UUID
) -> TemplateRangeModel:
    """Create and add a new range template to the database.

    Args:
    ----
        db (Session): Database connection.
        range_template (TemplateRangeSchema): Dictionary containing OpenLabsRange data.
        owner_id (uuid.UUID): The ID of the user who owns this template.

    Returns:
    -------
        OpenLabsRange: The newly created range template.

    """
    range_template = TemplateRangeSchema(**range_template.model_dump())
    range_dict = range_template.model_dump(exclude={"vpcs"})

    range_dict["owner_id"] = owner_id

    # Create the Range object (No commit yet)
    range_obj = TemplateRangeModel(**range_dict)
    db.add(range_obj)  # Stage the range

    # Build range ID
    range_id = TemplateRangeID(id=range_obj.id)

    # Create VPCs and associate them with the range (No commit yet)
    vpc_objects = [
        await create_vpc_template(db, vpc_data, owner_id, range_id)
        for vpc_data in range_template.vpcs
    ]
    # range_obj.vpcs = vpc_objects
    db.add_all(vpc_objects)  # Stage VPCs

    # Commit everything in one transaction
    await db.commit()

    return range_obj


async def delete_range_template(
    db: AsyncSession, range_model: TemplateRangeModel
) -> bool:
    """Delete a standalone range template.

    Only allows deletion if the subnet template is standalone.

    Args:
    ----
        db (Sessions): Database connection.
        range_model (TemplateRangeModel): Range template model object.

    Returns:
    -------
        bool: True if successfully delete. False otherwise.

    """
    if not range_model.is_standalone():
        log_msg = (
            "Cannot delete range template because it is not a standalone template."
        )
        logger.error(log_msg)
        return False

    await db.delete(range_model)
    await db.commit()
    return True

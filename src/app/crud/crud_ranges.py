import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.range_models import BlueprintRangeModel, DeployedRangeModel
from ..models.subnet_models import BlueprintSubnetModel, DeployedSubnetModel
from ..models.vpc_models import BlueprintVPCModel, DeployedVPCModel
from ..schemas.range_schemas import (
    BlueprintRangeCreateSchema,
    BlueprintRangeHeaderSchema,
    BlueprintRangeSchema,
    DeployedRangeCreateSchema,
    DeployedRangeHeaderSchema,
    DeployedRangeKeySchema,
    DeployedRangeSchema,
)
from .crud_vpcs import build_blueprint_vpc_models, build_deployed_vpc_models

logger = logging.getLogger(__name__)


# ==================== Blueprints =====================


async def get_blueprint_range_headers(
    db: AsyncSession,
    user_id: int,
    is_admin: bool = False,
) -> list[BlueprintRangeHeaderSchema]:
    """Get list of range blueprint headers.

    Args:
    ----
        db (Session): Database connection.
        user_id (int): ID of user.
        is_admin (bool): Admins can see other user's blueprints.

    Returns:
    -------
        list[BlueprintRangeHeaderSchema]: List of blueprint range header schemas.

    """
    stmt = select(
        BlueprintRangeModel.id,
        BlueprintRangeModel.name,
        BlueprintRangeModel.provider,
        BlueprintRangeModel.vnc,
        BlueprintRangeModel.vpn,
    ).select_from(BlueprintRangeModel)

    # If not admin, we need to get the user's own blueprints
    # and also blueprints shared with them through workspaces
    if not is_admin:
        try:
            from .crud_blueprint_permissions import get_user_workspaces_with_blueprint_access
            from sqlalchemy import or_, func

            # First, get a list of blueprints shared through workspaces
            # Use a subquery to find all blueprint IDs the user has access to via permissions
            from ..models.blueprint_permission_model import BlueprintPermissionModel
            from ..enums.permissions import PermissionEntityType

            # Filter for owner or user with permissions
            stmt = stmt.filter(or_(
                BlueprintRangeModel.owner_id == user_id,
                BlueprintRangeModel.id.in_(
                    select(BlueprintPermissionModel.blueprint_id)
                    .where(BlueprintPermissionModel.blueprint_type == "range_blueprints")
                    .where(BlueprintPermissionModel.entity_type == PermissionEntityType.USER)
                    .where(BlueprintPermissionModel.entity_id == user_id)
                )
            ))
        except Exception as e:
            logger.error(f"Error including shared blueprints: {e}")
            # Fallback to just getting owned blueprints
            stmt = stmt.filter(BlueprintRangeModel.owner_id == user_id)

    result = await db.execute(stmt)

    range_headers = [
        BlueprintRangeHeaderSchema.model_validate(row_mapping)
        for row_mapping in result.mappings().all()
    ]

    logger.info(
        "Fetched %s range blueprint headers for user: %s.",
        len(range_headers),
        user_id,
    )
    return range_headers


async def get_blueprint_range(
    db: AsyncSession, range_id: int, user_id: int, is_admin: bool = False
) -> BlueprintRangeSchema | None:
    """Get range blueprint by ID.

    Args:
    ----
        db (Session): Database connection.
        range_id (int): ID of the range blueprint.
        user_id (int): ID of the user requesting data.
        is_admin (bool): Admins can see other user's blueprints.

    Returns:
    -------
        Optional[BlueprintRangeSchema]: Range blueprint data if it exists in the database.

    """
    options = [
        selectinload(BlueprintRangeModel.vpcs)
        .selectinload(BlueprintVPCModel.subnets)
        .selectinload(BlueprintSubnetModel.hosts),
    ]
    range_model = await db.get(BlueprintRangeModel, range_id, options=options)

    if not range_model:
        logger.info(
            "Failed to fetch range blueprint: %s. Not found in database!", range_id
        )
        return None

    # First check direct ownership or admin 
    if is_admin or range_model.owner_id == user_id:
        logger.debug("Fetched range blueprint: %s for user %s (owner/admin).", range_id, user_id)
        return BlueprintRangeSchema.model_validate(range_model)
        
    # If not owner or admin, check for permission through workspace
    try:
        from .crud_blueprint_permissions import check_user_blueprint_access
        from ..enums.permissions import PermissionType
        
        # Check if user has access through workspace permissions
        has_access = await check_user_blueprint_access(
            db, 
            user_id, 
            "range_blueprints", 
            range_id, 
            PermissionType.READ
        )
        
        if has_access:
            logger.debug("Fetched range blueprint: %s for user %s (via workspace permission).", range_id, user_id)
            return BlueprintRangeSchema.model_validate(range_model)
    except Exception as e:
        logger.error(f"Error checking blueprint permissions: {e}")

    logger.warning(
        "User: %s is not authorized to fetch range blueprint: %s.", user_id, range_id
    )
    return None


def build_blueprint_range_models(
    ranges: list[BlueprintRangeCreateSchema], user_id: int
) -> list[BlueprintRangeModel]:
    """Build a list of blueprint range ORM models from creation schemas.

    **Note:** These models will only contain the data available in the
    schemas (i.e. no database ID).

    Args:
    ----
        ranges (list[BlueprintRangeCreateSchema]): Range object data.
        user_id (int): User who created the subnets.

    Returns:
    -------
        list[BlueprintRangeModel]: Corresponding blueprint range models.

    """
    range_models: list[BlueprintRangeModel] = []
    for range_schema in ranges:
        range_model = BlueprintRangeModel(
            **range_schema.model_dump(exclude={"vpcs"}), owner_id=user_id
        )
        range_model.vpcs = build_blueprint_vpc_models(range_schema.vpcs, user_id)
        range_models.append(range_model)

    logger.debug(
        "Build %s blueprint range models for user: %s.", len(range_models), user_id
    )
    return range_models


async def create_blueprint_range(
    db: AsyncSession,
    blueprint: BlueprintRangeCreateSchema,
    user_id: int,
) -> BlueprintRangeHeaderSchema:
    """Create and add a new range blueprint to the database session.

    **Note:** This function only adds ranges to the database session. It is the responsibility
    of the caller to commit the changes to the database or rollback in the event of
    a failure.

    Args:
    ----
        db (Session): Database connection.
        blueprint (BlueprintRangeCreateSchema): Pydantic model of range blueprint data without IDs.
        user_id (int): User who owns the new range blueprint.

    Returns:
    -------
        BlueprintRangeHeaderSchema: The newly created range blueprint header data with it's ID.

    """
    built_models = build_blueprint_range_models([blueprint], user_id)

    # Sanity check that we only have a single range model
    if len(built_models) != 1:
        msg = f"Built {len(built_models) } range blueprint models from a single schema!"
        logger.error(msg)
        raise RuntimeError(msg)

    range_model = built_models[0]

    db.add(range_model)
    logger.debug(
        "Added range blueprint model with name: %s to database session.",
        range_model.name,
    )

    try:
        await db.flush()
        await db.refresh(range_model)
        logger.debug(
            "Successfully flushed range blueprint: %s owned by user: %s.",
            range_model.id,
            user_id,
        )
    except SQLAlchemyError as e:
        logger.exception(
            "Database error while flushing range blueprint to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error while flushing range blueprint to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise

    return BlueprintRangeHeaderSchema.model_validate(range_model)


async def delete_blueprint_range(
    db: AsyncSession, range_id: int, user_id: int, is_admin: bool = False
) -> BlueprintRangeHeaderSchema | None:
    """Delete a range blueprint.

    This function only adds delete queries to the database session. It is the responsibility of
    the caller to commit the changes to the database or rollback in the event of a failure.

    Args:
    ----
        db (Sessions): Database connection.
        range_id (int): ID of the range blueprint.
        user_id (int): ID of user initiating the delete.
        is_admin (bool): Admins can delete other user's blueprints.

    Returns:
    -------
        Optional[BlueprintRangeHeaderSchema]: Range header data if it exists in database and was successfully deleted.

    """
    range_model = await db.get(BlueprintRangeModel, range_id)
    if not range_model:
        logger.warning(
            "Range blueprint: %s not found for deletion as user: %s. Does user have permissions?",
            range_id,
            user_id,
        )
        return None

    if not range_model.is_standalone():
        logger.info(
            "Failed to delete range blueprint: %s. Not a standalone blueprint!",
            range_model.id,
        )
        return None

    if not is_admin and range_model.owner_id != user_id:
        logger.warning(
            "User: %s is not authorized to delete range blueprint: %s.",
            user_id,
            range_model.id,
        )
        return None

    try:
        await db.delete(range_model)
        await db.flush()
        logger.debug(
            "Successfully marked range blueprint: %s for deletion.", range_model.id
        )
    except SQLAlchemyError as e:
        logger.exception(
            "Database error while marking range blueprint: %s for deletion for user: %s. Exception: %s.",
            range_model.id,
            user_id,
            e,
        )
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error while marking range blueprint: %s for deletion for user: %s. Exception: %s.",
            range_model.id,
            user_id,
            e,
        )
        raise

    return BlueprintRangeHeaderSchema.model_validate(range_model)


# ==================== Deployed (Instances) =====================


async def get_deployed_range_headers(
    db: AsyncSession,
    user_id: int,
    is_admin: bool = False,
) -> list[DeployedRangeHeaderSchema]:
    """Get list of deployed range headers.

    Args:
    ----
        db (Session): Database connection.
        user_id (int): ID of user.
        is_admin (bool): Admins can see other user's blueprints.

    Returns:
    -------
        list[DeployedRangeHeaderSchema]: List of deployed range header schemas.

    """
    stmt = select(
        DeployedRangeModel.id,
        DeployedRangeModel.name,
        DeployedRangeModel.provider,
        DeployedRangeModel.vnc,
        DeployedRangeModel.vpn,
        DeployedRangeModel.description,
        DeployedRangeModel.date,
        DeployedRangeModel.state,
        DeployedRangeModel.region,
    ).select_from(DeployedRangeModel)

    if not is_admin:
        stmt = stmt.filter(DeployedRangeModel.owner_id == user_id)

    result = await db.execute(stmt)

    range_headers = [
        DeployedRangeHeaderSchema.model_validate(row_mapping)
        for row_mapping in result.mappings().all()
    ]

    logger.info(
        "Fetched %s deployed range headers for user: %s.",
        len(range_headers),
        user_id,
    )
    return range_headers


async def get_deployed_range(
    db: AsyncSession, range_id: int, user_id: int, is_admin: bool = False
) -> DeployedRangeSchema | None:
    """Get deployed range by ID.

    Args:
    ----
        db (Session): Database connection.
        range_id (int): ID of the deployed range.
        user_id (int): ID of the user requesting data.
        is_admin (bool): Admins can see other user's deployed ranges.

    Returns:
    -------
        Optional[DeployedRangeSchema]: Deployed range data if it exists in the database.

    """
    options = [
        selectinload(DeployedRangeModel.vpcs)
        .selectinload(DeployedVPCModel.subnets)
        .selectinload(DeployedSubnetModel.hosts)
    ]
    range_model = await db.get(DeployedRangeModel, range_id, options=options)

    if not range_model:
        logger.info(
            "Failed to fetch deployed range: %s. Not found in database!", range_id
        )
        return None

    if is_admin or range_model.owner_id == user_id:
        logger.debug("Fetched deployed range: %s for user %s.", range_id, user_id)
        return DeployedRangeSchema.model_validate(range_model)

    logger.warning(
        "User: %s is not authorized to fetch deployed range: %s.", user_id, range_id
    )
    return None

async def get_deployed_range_key(
    db: AsyncSession,
    range_id: int,
    user_id: int,
    is_admin: bool = False,
) -> DeployedRangeKeySchema | None:
    """Get the SSH private key for a deployed range by ID.

    Optimized to only query the required 'range_private_key' column.

    Args:
    ----
        db (Session): Database connection.
        range_id (int): ID of the deployed range.
        user_id (int): ID of user requesting the key.
        is_admin (bool): Admins can access other user's range keys.

    Returns:
    -------
        Optional[DeployedRangeKeySchema]: Deployed range key data if the range exists and the user is authorized, otherwise None.

    """
    stmt = select(DeployedRangeModel.range_private_key).where(
        DeployedRangeModel.id == range_id
    )

    if not is_admin:
        stmt = stmt.where(DeployedRangeModel.owner_id == user_id)

    try:
        range_private_key = await db.scalar(stmt)

        if range_private_key is None:
            logger.warning(
                "Failed to fetch deployed range key for range: %s for user %s. Range not found or unauthorized.",
                range_id,
                user_id,
            )
            return None

        logger.debug(
            "Fetched deployed range key for range: %s for user %s.", range_id, user_id
        )
        return DeployedRangeKeySchema(range_private_key=range_private_key)

    except SQLAlchemyError as e:
        logger.exception(
            "Database error fetching deployed range key for range: %s for user %s. Exception: %s",
            range_id,
            user_id,
            e,
        )
        raise

    except Exception as e:
         logger.exception(
            "Unexpected error fetching deployed range key for range: %s for user %s. Exception: %s",
            range_id,
            user_id,
            e,
        )
         raise


def build_deployed_range_models(
    ranges: list[DeployedRangeCreateSchema], user_id: int
) -> list[DeployedRangeModel]:
    """Build a list of deployed range ORM models from creation schemas.

    **Note:** These models will only contain the data available in the
    schemas (i.e. no database ID).

    Args:
    ----
        ranges (list[DeployedRangeCreateSchema]): Range object data.
        user_id (int): User who created the ranges.

    Returns:
    -------
        list[DeployedRangeModels]: Corresponding deployed range models.

    """
    range_models: list[DeployedRangeModel] = []
    for range_schema in ranges:
        range_model = DeployedRangeModel(
            **range_schema.model_dump(exclude={"vpcs"}), owner_id=user_id
        )
        range_model.vpcs = build_deployed_vpc_models(range_schema.vpcs, user_id)
        range_models.append(range_model)

    logger.debug(
        "Build %s deployed range models for user: %s.", len(range_models), user_id
    )
    return range_models


async def create_deployed_range(
    db: AsyncSession,
    range_schema: DeployedRangeCreateSchema,
    user_id: int,
) -> DeployedRangeHeaderSchema:
    """Create and add a new deployed range to the database session.

    **Note:** This function only adds ranges to the database session. It is the responsibility
    of the caller to commit the changes to the database or rollback in the event of
    a failure.

    Args:
    ----
        db (Session): Database connection.
        range_schema (DeployedRangeCreateSchema): Pydantic model of deployed range data without IDs.
        user_id (int): User who owns the new deployed range.

    Returns:
    -------
        DeployedRangeHeaderSchema: The newly created deployed range header data with it's ID.

    """
    built_models = build_deployed_range_models([range_schema], user_id)

    # Sanity check that we only have a single range model
    if len(built_models) != 1:
        msg = f"Built {len(built_models) } deployed range models from a single schema!"
        logger.error(msg)
        raise RuntimeError(msg)

    range_model = built_models[0]

    db.add(range_model)
    logger.debug(
        "Added deployed range model with name: %s to database session.",
        range_model.name,
    )

    try:
        await db.flush()
        await db.refresh(range_model)
        logger.debug(
            "Successfully flushed deployed range: %s owned by user: %s.",
            range_model.id,
            user_id,
        )
    except SQLAlchemyError as e:
        logger.exception(
            "Database error while flushing deployed range to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error while flushing deployed range to database session for user: %s. Exception: %s.",
            user_id,
            e,
        )
        raise

    return DeployedRangeHeaderSchema.model_validate(range_model)


async def delete_deployed_range(
    db: AsyncSession, range_id: int, user_id: int, is_admin: bool = False
) -> DeployedRangeHeaderSchema | None:
    """Delete a deployed range.

    This function only adds delete queries to the database session. It is the responsibility of
    the caller to commit the changes to the database or rollback in the event of a failure.

    Args:
    ----
        db (Sessions): Database connection.
        range_id (int): ID of the deployed range.
        user_id (int): ID of user initiating the delete.
        is_admin (bool): Admins can delete other user's deployed ranges.

    Returns:
    -------
        Optional[DeployedRangeHeaderSchema]: Deployed range header data if it exists in database and was successfully deleted.

    """
    range_model = await db.get(DeployedRangeModel, range_id)
    if not range_model:
        logger.warning(
            "Deployed range: %s not found for deletion as user: %s. Does user have permissions?",
            range_id,
            user_id,
        )
        return None

    if not is_admin and range_model.owner_id != user_id:
        logger.warning(
            "User: %s is not authorized to delete deployed range: %s.",
            user_id,
            range_model.id,
        )
        return None

    try:
        await db.delete(range_model)
        await db.flush()
        logger.debug(
            "Successfully marked deployed range: %s for deletion.", range_model.id
        )
    except SQLAlchemyError as e:
        logger.exception(
            "Database error while marking deployed range: %s for deletion for user: %s. Exception: %s.",
            range_model.id,
            user_id,
            e,
        )
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error while marking deployed range: %s for deletion for user: %s. Exception: %s.",
            range_model.id,
            user_id,
            e,
        )
        raise

    return DeployedRangeHeaderSchema.model_validate(range_model)

from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_hosts import (
    create_blueprint_host,
    delete_blueprint_host,
    get_blueprint_host,
    get_blueprint_host_headers,
)
from ...crud.crud_ranges import (
    create_blueprint_range,
    delete_blueprint_range,
    get_blueprint_range,
    get_blueprint_range_headers,
)
from ...crud.crud_subnets import (
    create_blueprint_subnet,
    delete_blueprint_subnet,
    get_blueprint_subnet,
    get_blueprint_subnet_headers,
)
from ...crud.crud_vpcs import (
    create_blueprint_vpc,
    delete_blueprint_vpc,
    get_blueprint_vpc,
    get_blueprint_vpc_headers,
)

from ...crud.crud_blueprint_permissions import (
    create_blueprint_permission,
    delete_blueprint_permission,
    get_blueprint_permission,
    get_blueprint_permissions_by_blueprint,
)

from ...schemas.blueprint_permission_schema import (
    BlueprintPermissionCreateSchema,
    BlueprintPermissionSchema,
)

from ...schemas.message_schema import MessageSchema
from ...models.blueprint_permission_model import BlueprintPermissionModel


from ...models.user_model import UserModel
from ...schemas.host_schemas import (
    BlueprintHostCreateSchema,
    BlueprintHostHeaderSchema,
    BlueprintHostSchema,
)
from ...schemas.message_schema import MessageSchema
from ...schemas.range_schemas import (
    BlueprintRangeCreateSchema,
    BlueprintRangeHeaderSchema,
    BlueprintRangeSchema,
)
from ...schemas.subnet_schemas import (
    BlueprintSubnetCreateSchema,
    BlueprintSubnetHeaderSchema,
    BlueprintSubnetSchema,
)
from ...schemas.vpc_schemas import (
    BlueprintVPCCreateSchema,
    BlueprintVPCHeaderSchema,
    BlueprintVPCSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blueprints", tags=["blueprints"])


# ==================== Ranges =====================


@router.get("/ranges")
async def get_blueprint_range_headers_endpoint(
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[BlueprintRangeHeaderSchema]:
    """Get a list of blueprint range headers.

    Args:
    ----
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[BlueprintRangeHeaderSchema]: List of blueprint range headers. For admin users, shows all blueprints.
                               For regular users, shows only blueprints they own.

    """
    range_headers = await get_blueprint_range_headers(
        db, current_user.id, current_user.is_admin
    )

    if not range_headers:
        logger.info(
            "No range blueprint headers found for user: %s (%s)",
            current_user.email,
            current_user.id,
        )
        msg = (
            "No range blueprints found!"
            if current_user.is_admin
            else "Unable to find any range blueprints that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )

    logger.info(
        "Successfully retrieved %s range blueprint headers for user: %s (%s).",
        len(range_headers),
        current_user.email,
        current_user.id,
    )

    return range_headers


@router.get("/ranges/{blueprint_id}")
async def get_blueprint_range_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintRangeSchema:
    """Get a range blueprint.

    Args:
    ----
        blueprint_id (int): ID of the range blueprint.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintRangeSchema: Range blueprint data from database. Admin users can access any blueprint.

    """
    blueprint_range = await get_blueprint_range(
        db, blueprint_id, current_user.id, current_user.is_admin
    )

    if not blueprint_range:
        logger.info(
            "Failed to retrieve range blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range blueprint with ID: {blueprint_id} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully retrieved range blueprint: %s for user: %s (%s).",
        blueprint_range.id,
        current_user.email,
        current_user.id,
    )

    return blueprint_range


@router.post("/ranges")
async def upload_blueprint_range_endpoint(
    blueprint_range: BlueprintRangeCreateSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintRangeHeaderSchema:
    """Upload a range blueprint.

    Args:
    ----
        blueprint_range (BlueprintRangeHeaderSchema): OpenLabs compliant blueprint range object.
        db (AsynSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintRangeHeaderSchema: Header info of the new range blueprint.

    """
    created_blueprint = await create_blueprint_range(
        db, blueprint_range, current_user.id
    )

    logger.info(
        "Successfully processed range blueprint creation request for user: %s (%s). Blueprint ID: %s",
        current_user.email,
        current_user.id,
        created_blueprint.id,
    )

    return BlueprintRangeHeaderSchema.model_validate(created_blueprint)


@router.delete("/ranges/{blueprint_id}")
async def delete_blueprint_range_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> MessageSchema:
    """Delete a blueprint range.

    Args:
    ----
        blueprint_id (str): Id of the blueprint range.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        MessageSchema: Message regarding status of deletion.

    """
    deleted_blueprint = await delete_blueprint_range(
        db, blueprint_id, current_user.id, current_user.is_admin
    )
    if not deleted_blueprint:
        logger.info(
            "Failed to delete range blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range blueprint with id: {blueprint_id} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully deleted range blueprint: %s (%s) for user: %s (%s).",
        deleted_blueprint.name,
        deleted_blueprint.id,
        current_user.email,
        current_user.id,
    )

    return MessageSchema(
        message=f"Range blueprint: {deleted_blueprint.name} ({deleted_blueprint.id}) was successfully deleted!"
    )


# ==================== VPCs =====================


@router.get("/vpcs")
async def get_blueprint_vpc_headers_endpoint(
    standalone_only: bool = True,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[BlueprintVPCHeaderSchema]:
    """Get a list of blueprint VPC headers.

    Args:
    ----
        standalone_only (bool): Return only standalone VPC blueprints (not part of a range blueprint). Defaults to True.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[BlueprintVPCHeaderSchema]: List of VPC blueprint sheaders owned by the current user.

    """
    vpc_headers = await get_blueprint_vpc_headers(
        db, current_user.id, current_user.is_admin, standalone_only
    )

    if not vpc_headers:
        logger.info(
            "No VPC blueprint headers found for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        standalone_text = " standalone" if standalone_only else ""
        msg = (
            f"No{standalone_text} VPC blueprints found!"
            if current_user.is_admin
            else f"Unable to find any{standalone_text} VPC blueprints that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )

    logger.info(
        "Sucessfully retrieved %s VPC blueprint headers for user: %s (%s).",
        len(vpc_headers),
        current_user.email,
        current_user.id,
    )

    return vpc_headers


@router.get("/vpcs/{blueprint_id}")
async def get_blueprint_vpc_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintVPCSchema:
    """Get a bluerprint VPC.

    Args:
    ----
        blueprint_id (int): ID of the VPC blueprint.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintVPCSchema: Blueprint VPC data from database if it belongs to the user.

    """
    blueprint_vpc = await get_blueprint_vpc(
        db, blueprint_id, current_user.id, current_user.is_admin
    )
    if not blueprint_vpc:
        logger.info(
            "Failed to retrieve VPC blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VPC blueprint with ID: {blueprint_id} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully retrieved VPC blueprint: %s for user: %s (%s).",
        blueprint_vpc.id,
        current_user.email,
        current_user.id,
    )

    return blueprint_vpc


@router.post("/vpcs")
async def upload_blueprint_vpc_endpoint(
    blueprint_vpc: BlueprintVPCCreateSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintVPCHeaderSchema:
    """Upload a VPC blueprint.

    Args:
    ----
        blueprint_vpc (BlueprintVPCCreateSchema): OpenLabs compliant blueprint VPC object.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintVPCHeaderSchema: Header info of the new VPC blueprint.

    """
    # No range ID since this is a standalone blueprint
    created_blueprint = await create_blueprint_vpc(
        db, blueprint_vpc, current_user.id, range_id=None
    )

    logger.info(
        "Successfully processed VPC blueprint creation request for user: %s (%s). Blueprint ID: %s.",
        current_user.email,
        current_user.id,
        created_blueprint.id,
    )

    return BlueprintVPCHeaderSchema.model_validate(created_blueprint)


@router.delete("/vpcs/{blueprint_id}")
async def delete_blueprint_vpc_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> MessageSchema:
    """Delete a VPC blueprint.

    Args:
    ----
        blueprint_id (int): Id of the VPC blueprint.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        MessageSchema: Message regarding status of deletion.

    """
    deleted_blueprint = await delete_blueprint_vpc(
        db, blueprint_id, current_user.id, current_user.is_admin
    )
    if not deleted_blueprint:
        logger.info(
            "Failed to delete VPC blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VPC blueprint with id: {blueprint_id} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully deleted VPC blueprint: %s (%s) for user: %s (%s).",
        deleted_blueprint.name,
        deleted_blueprint.id,
        current_user.email,
        current_user.id,
    )

    return MessageSchema(
        message=f"VPC blueprint: {deleted_blueprint.name} ({deleted_blueprint.id}) was successfully deleted!"
    )


# ==================== Subnets =====================


@router.get("/subnets")
async def get_blueprint_subnet_headers_endpoint(
    standalone_only: bool = True,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[BlueprintSubnetHeaderSchema]:
    """Get a list of blueprint subnet headers.

    Args:
    ----
        standalone_only (bool): Return only standalone subnet blueprints (not part of a range/vpc blueprint). Defaults to True.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[BlueprintSubnetHeaderSchema]: List of subnet blueprint headers owned by the current user.

    """
    subnet_headers = await get_blueprint_subnet_headers(
        db, current_user.id, current_user.is_admin, standalone_only
    )

    if not subnet_headers:
        logger.info(
            "No subnet blueprint headers found for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        standalone_text = " standalone" if standalone_only else ""
        detail = (
            f"No{standalone_text} subnet blueprints found!"
            if current_user.is_admin
            else f"Unable to find any{standalone_text} subnet blueprints that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return subnet_headers


@router.get("/subnets/{blueprint_id}")
async def get_blueprint_subnet_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintSubnetSchema:
    """Get a subnet blueprint.

    Args:
    ----
        blueprint_id (int): ID of the subnet blueprint.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintSubnetSchema: Subnet data from database. Admin users can access any blueprint.

    """
    blueprint_subnet = await get_blueprint_subnet(
        db, blueprint_id, current_user.id, current_user.is_admin
    )
    if not blueprint_subnet:
        logger.info(
            "Failed to retrieve subnet blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subnet blueprint with ID: {blueprint_id} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully retrieved subnet blueprint: %s for user: %s (%s).",
        blueprint_subnet.id,
        current_user.email,
        current_user.id,
    )

    return blueprint_subnet


@router.post("/subnets")
async def upload_blueprint_subnet_endpoint(
    blueprint_subnet: BlueprintSubnetCreateSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintSubnetHeaderSchema:
    """Upload a subnet blueprint.

    Args:
    ----
        blueprint_subnet (BlueprintSubnetCreateSchema): OpenLabs compliant subnet blueprint object.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintSubnetHeaderSchema: Header info of the new subnet blueprint.

    """
    # No VPC ID since this a standalone blueprint
    created_blueprint = await create_blueprint_subnet(
        db, blueprint_subnet, current_user.id, vpc_id=None
    )

    logger.info(
        "Successfully processed subnet blueprint creation request for user: %s (%s). Blueprint ID: %s",
        current_user.email,
        current_user.id,
        created_blueprint.id,
    )

    return BlueprintSubnetHeaderSchema.model_validate(created_blueprint)


@router.delete("/subnets/{blueprint_id}")
async def delete_subnet_blueprint_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> MessageSchema:
    """Delete a subnet blueprint.

    Args:
    ----
        blueprint_id (int): Id of the subnet blueprint.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        MessageSchema: Message regarding status of deletion.

    """
    deleted_blueprint = await delete_blueprint_subnet(
        db, blueprint_id, current_user.id, current_user.is_admin
    )
    if not deleted_blueprint:
        logger.info(
            "Failed to delete subnet blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subnet blueprint with id: {blueprint_id} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully deleted subnet blueprint: %s (%s) for user: %s (%s).",
        deleted_blueprint.name,
        deleted_blueprint.id,
        current_user.email,
        current_user.id,
    )

    return MessageSchema(
        message=f"Subnet blueprint: {deleted_blueprint.name} ({deleted_blueprint.id}) was successfully deleted!"
    )


# ==================== Hosts =====================


@router.get("/hosts")
async def get_blueprint_host_headers_endpoint(
    standalone_only: bool = True,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> list[BlueprintHostHeaderSchema]:
    """Get a list of host blueprint headers.

    Args:
    ----
        standalone_only (bool): Return only standalone host blueprint (not part of a range/vpc/subnet blueprint). Defaults to True.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        list[BlueprintHostHeaderSchema]: List of host blueprint headers owned by the current user.

    """
    host_headers = await get_blueprint_host_headers(
        db, current_user.id, current_user.is_admin, standalone_only
    )
    if not host_headers:
        logger.info(
            "No host blueprint headers found for user: %s (%s).",
            current_user.email,
            current_user.id,
        )
        standalone_text = " standalone" if standalone_only else ""
        msg = (
            f"No{standalone_text} host blueprints found!"
            if current_user.is_admin
            else f"Unable to find any{standalone_text} host blueprints that you own!"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )

    return host_headers


@router.get("/hosts/{blueprint_id}")
async def get_blueprint_host_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintHostSchema:
    """Get a host blueprint.

    Args:
    ----
        blueprint_id (int): Id of the host blueprint.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintHostSchema: Host data from database. Admin users can access any blueprint.

    """
    blueprint_host = await get_blueprint_host(
        db, blueprint_id, current_user.id, current_user.is_admin
    )
    if not blueprint_host:
        logger.info(
            "Failed to retrieve host blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host blueprint with ID: {blueprint_id} not found or you don't have access to it!",
        )

    return blueprint_host


@router.post("/hosts")
async def upload_blueprint_host_endpoint(
    blueprint_host: BlueprintHostCreateSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> BlueprintHostHeaderSchema:
    """Upload a host blueprint.

    Args:
    ----
        blueprint_host (BlueprintHostCreateSchema): OpenLabs compliant host blueprint object.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        BlueprintHostHeaderSchema: Header info of the new host blueprint.

    """
    # No subnet ID since this a standalone blueprint
    created_blueprint = await create_blueprint_host(
        db, blueprint_host, current_user.id, subnet_id=None
    )

    logger.info(
        "Successfully processed host blueprint creation request for user: %s (%s). Blueprint ID: %s",
        current_user.email,
        current_user.id,
        created_blueprint.id,
    )

    return BlueprintHostHeaderSchema.model_validate(created_blueprint)


@router.delete("/hosts/{blueprint_id}")
async def delete_blueprint_host_endpoint(
    blueprint_id: int,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
) -> MessageSchema:
    """Delete a host blueprint.

    Args:
    ----
        blueprint_id (int): Id of the host blueprint.
        db (AsyncSession): Async database connection.
        current_user (UserModel): Currently authenticated user.

    Returns:
    -------
        MessageSchema: Message regarding status of deletion.

    """
    deleted_blueprint = await delete_blueprint_host(
        db, blueprint_id, current_user.id, current_user.is_admin
    )
    if not deleted_blueprint:
        logger.info(
            "Failed to delete host blueprint: %s for user: %s (%s).",
            blueprint_id,
            current_user.email,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host blueprint with id: {blueprint_id} not found or you don't have access to it!",
        )

    logger.info(
        "Successfully deleted host blueprint: %s (%s) for user: %s (%s).",
        deleted_blueprint.hostname,
        deleted_blueprint.id,
        current_user.email,
        current_user.id,
    )

    return MessageSchema(
        message=f"Host blueprint: {deleted_blueprint.hostname} ({deleted_blueprint.id}) was successfully deleted!"
    )

@router.post("/{blueprint_type}/{blueprint_id}/permissions", response_model=BlueprintPermissionSchema)
async def add_permission_to_blueprint(
    permission: BlueprintPermissionCreateSchema,
    blueprint_type: str = Path(
        ...,
        description="Type of the blueprint (range, vpc, subnet, host)",
        examples=[
            "range_blueprints",
            "vpc_blueprints",
            "subnet_blueprints",
            "host_blueprints",
        ],
    ),
    blueprint_id: int = Path(
        ...,
        description="ID of the blueprint",
    ),
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> BlueprintPermissionModel:
    """Add a permission to a blueprint.

    Args:
        permission (BlueprintPermissionCreateSchema): Permission data to be added.
        blueprint_type (str): Type of the blueprint (range, vpc, subnet, host).
        blueprint_id (int): ID of the blueprint.
        current_user (UserModel): Currently authenticated user.
        db (AsyncSession): Async database connection.

    Returns:
        BlueprintPermissionModel: The created permission object.

    Raises:
        HTTPException: If the permission could not be created or if the user does not have access to the blueprint.
    """
    # Only admin or blueprint owners can add permissions
    # This would need to check ownership based on the blueprint type
    # For now, we're simplifying by only allowing admins
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can manage permissions",
        )

    # Verify that the blueprint_type and blueprint_id in the path match the permission data
    if (
        permission.blueprint_type != blueprint_type
        or permission.blueprint_id != blueprint_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Blueprint type and ID in path must match permission data",
        )

    return await create_blueprint_permission(db, permission)


@router.get("/{blueprint_type}/{blueprint_id}/permissions", response_model=BlueprintPermissionSchema)
async def get_permission_for_blueprint(
    blueprint_type: str = Path(
        ...,
        description="Type of the blueprint (range, vpc, subnet, host)",
        examples=[
            "range_blueprints",
            "vpc_blueprints",
            "subnet_blueprints",
            "host_blueprints",
        ],
    ),
    blueprint_id: int = Path(
        ...,
        description="ID of the blueprint",
    ),
    current_user: UserModel = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> list[BlueprintPermissionModel]:
    """Get a permission for a blueprint.

    Args:
        blueprint_type (str): Type of the blueprint (range, vpc, subnet, host).
        blueprint_id (int): ID of the blueprint.
        current_user (UserModel): Currently authenticated user.
        db (AsyncSession): Async database connection.

    Returns:
        BlueprintPermissionModel: The permission object.

    Raises:
        HTTPException: If the permission could not be retrieved or if the user does not have access to the blueprint.
    """
    # Only admin or blueprint owners can view permissions
    # This would need to check ownership based on the blueprint type
    # For now, we're simplifying by only allowing admins
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view permissions",
        )

    return await get_blueprint_permissions_by_blueprint(db, blueprint_type, blueprint_id)

@router.delete(
    "/{blueprint_type}/{blueprint_id}/permissions/{permission_id}",
    response_model=MessageSchema,
)
async def delete_permission_from_blueprint(
    blueprint_type: str = Path(
        ..., description="The type of blueprint (range, vpc, etc.)"
    ),
    blueprint_id: int = Path(..., description="The ID of the blueprint"),
    permission_id: UUID = Path(..., description="The ID of the permission to delete"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> MessageSchema:
    """Delete a permission from a blueprint.
    Args:
    ----
        blueprint_type (str): The type of blueprint.
        blueprint_id (int): The ID of the blueprint.
        permission_id (UUID): The ID of the permission to delete.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.
    Returns:
    -------
        MessageSchema: Success message.
    """
    # Only admin or blueprint owners can delete permissions
    # This would need to check ownership based on the blueprint type
    # For now, we're simplifying by only allowing admins
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can manage permissions",
        )

    # Get the permission to check if it belongs to the specified blueprint
    permission = await get_blueprint_permission(db, permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    # Verify that the permission is for the specified blueprint
    if (
        permission.blueprint_type != blueprint_type
        or permission.blueprint_id != blueprint_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission does not belong to the specified blueprint",
        )

    # Delete the permission
    success = await delete_blueprint_permission(db, permission_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete permission",
        )

    return MessageSchema(message="Permission deleted successfully")
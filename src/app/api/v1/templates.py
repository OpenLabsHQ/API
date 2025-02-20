from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.db.database import async_get_db
from ...crud.crud_hosts import create_host, get_host, get_host_headers
from ...crud.crud_ranges import create_range, get_range, get_range_headers
from ...crud.crud_subnets import create_subnet, get_subnet, get_subnet_headers
from ...crud.crud_vpcs import create_vpc, get_vpc, get_vpc_headers
from ...schemas.template_host_schema import (
    TemplateHostBaseSchema,
    TemplateHostID,
    TemplateHostSchema,
)
from ...schemas.template_range_schema import (
    OpenLabsRangeBaseSchema,
    OpenLabsRangeHeaderSchema,
    OpenLabsRangeID,
    OpenLabsRangeSchema,
)
from ...schemas.template_subnet_schema import (
    TemplateSubnetBaseSchema,
    TemplateSubnetHeaderSchema,
    TemplateSubnetID,
    TemplateSubnetSchema,
)
from ...schemas.template_vpc_schema import (
    OpenLabsVPCBaseSchema,
    OpenLabsVPCHeaderSchema,
    OpenLabsVPCID,
    OpenLabsVPCSchema,
)
from ...validators.id import is_valid_uuid4

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/ranges")
async def get_range_template_headers(
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> list[OpenLabsRangeHeaderSchema]:
    """Get a list of range template headers.

    Args:
    ----
        db (AsyncSession): Async database connection.

    Returns:
    -------
        list[OpenLabsRangeID]: List of range template headers.

    """
    range_headers = await get_range_headers(db)

    if not range_headers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unable to find any range templates!",
        )

    return [
        OpenLabsRangeHeaderSchema.model_validate(header, from_attributes=True)
        for header in range_headers
    ]


@router.get("/ranges/{range_id}")
async def get_range_template(
    range_id: str, db: AsyncSession = Depends(async_get_db)  # noqa: B008
) -> OpenLabsRangeSchema:
    """Get a range template.

    Args:
    ----
        range_id (str): ID of the range.
        db (AsyncSession): Async database connection.

    Returns:
    -------
        OpenLabsRangeSchema: Range data from database.

    """
    if not is_valid_uuid4(range_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    openlabs_range = await get_range(db, OpenLabsRangeID(id=range_id))

    if not openlabs_range:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Range with id: {range_id} not found!",
        )

    return OpenLabsRangeSchema.model_validate(openlabs_range, from_attributes=True)


@router.post("/ranges")
async def upload_range_template(
    openlabs_range: OpenLabsRangeBaseSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> OpenLabsRangeID:
    """Upload a range template.

    Args:
    ----
        openlabs_range (OpenLabsRangeBaseSchema): OpenLabs compliant range object.
        db (AsynSession): Async database connection.

    Returns:
    -------
        OpenLabsRangeID: Identity of the range template.

    """
    created_range = await create_range(db, openlabs_range)
    return OpenLabsRangeID.model_validate(created_range, from_attributes=True)


@router.get("/vpcs")
async def get_vpc_template_headers(
    standalone_only: bool = True,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> list[OpenLabsVPCHeaderSchema]:
    """Get a list of vpc template headers.

    Args:
    ----
        standalone_only (bool): Return only standalone VPC templates (not part of a range template). Defaults to True.
        db (AsyncSession): Async database connection.

    Returns:
    -------
        list[OpenLabsVPCID]: List of vpc template headers.

    """
    vpc_headers = await get_vpc_headers(db, standalone_only=standalone_only)

    if not vpc_headers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unable to find any{" standalone" if standalone_only else ""} vpc templates!",
        )

    return [
        OpenLabsVPCHeaderSchema.model_validate(header, from_attributes=True)
        for header in vpc_headers
    ]


@router.get("/vpcs/{vpc_id}")
async def get_vpc_template(
    vpc_id: str, db: AsyncSession = Depends(async_get_db)  # noqa: B008
) -> OpenLabsVPCSchema:
    """Get a VPC template.

    Args:
    ----
        vpc_id (str): ID of the VPC.
        db (AsyncSession): Async database connection.

    Returns:
    -------
        OpenLabsVPCSchema: VPC data from database.

    """
    if not is_valid_uuid4(vpc_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    openlabs_vpc = await get_vpc(db, OpenLabsVPCID(id=vpc_id))

    if not openlabs_vpc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VPC with id: {vpc_id} not found!",
        )

    return OpenLabsVPCSchema.model_validate(openlabs_vpc, from_attributes=True)


@router.post("/vpcs")
async def upload_vpc_template(
    openlabs_vpc: OpenLabsVPCBaseSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> OpenLabsVPCID:
    """Upload a VPC template.

    Args:
    ----
        openlabs_vpc (OpenLabsVPCBaseSchema): OpenLabs compliant VPC object.
        db (AsyncSession): Async database connection.

    Returns:
    -------
        OpenLabsVPCID: Identity of the VPC template.

    """
    created_vpc = await create_vpc(db, openlabs_vpc)
    return OpenLabsVPCID.model_validate(created_vpc, from_attributes=True)


@router.get("/subnets")
async def get_subnet_template_headers(
    standalone_only: bool = True,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> list[TemplateSubnetHeaderSchema]:
    """Get a list of subnet template headers.

    Args:
    ----
        standalone_only (bool): Return only standalone subnet templates (not part of a range/vpc template). Defaults to True.
        db (AsyncSession): Async database connection.

    Returns:
    -------
        list[TemplateSubnetHeaderSchema]: List of subnet template headers.

    """
    subnet_headers = await get_subnet_headers(db, standalone_only=standalone_only)

    if not subnet_headers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unable to find any{" standalone" if standalone_only else ""} subnet templates!",
        )

    return [
        TemplateSubnetHeaderSchema.model_validate(header, from_attributes=True)
        for header in subnet_headers
    ]


@router.get("/subnets/{subnet_id}")
async def get_subnet_template(
    subnet_id: str, db: AsyncSession = Depends(async_get_db)  # noqa: B008
) -> TemplateSubnetSchema:
    """Get a subnet template.

    Args:
    ----
        subnet_id (str): ID of the subnet.
        db (AsyncSession): Async database connection.

    Returns:
    -------
        TemplateSubnetSchema: Subnet data from database.

    """
    if not is_valid_uuid4(subnet_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    openlabs_subnet = await get_subnet(db, TemplateSubnetID(id=subnet_id))

    if not openlabs_subnet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subnet with id: {subnet_id} not found!",
        )

    return TemplateSubnetSchema.model_validate(openlabs_subnet, from_attributes=True)


@router.post("/subnets")
async def upload_subnet_template(
    openlabs_subnet: TemplateSubnetBaseSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> TemplateSubnetID:
    """Upload a subnet template.

    Args:
    ----
        openlabs_subnet (TemplateSubnetBaseSchema): OpenLabs compliant subnet object.
        db (AsyncSession): Async database connection.

    Returns:
    -------
        TemplateSubnetID: Identity of the subnet template.

    """
    created_subnet = await create_subnet(db, openlabs_subnet)
    return TemplateSubnetID.model_validate(created_subnet, from_attributes=True)


@router.get("/hosts")
async def get_host_template_headers(
    standalone_only: bool = True,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> list[TemplateHostSchema]:
    """Get a list of host template headers.

    Args:
    ----
        standalone_only (bool): Return only standalone host templates (not part of a range/vpc/subnet template). Defaults to True.
        db (AsyncSession): Async database connection.

    Returns:
    -------
        list[TemplateHostID]: List of host template UUIDs.

    """
    host_headers = await get_host_headers(db, standalone_only=standalone_only)

    if not host_headers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unable to find any{" standalone" if standalone_only else ""} host templates!",
        )

    return [
        TemplateHostSchema.model_validate(header, from_attributes=True)
        for header in host_headers
    ]


@router.get("/hosts/{host_id}")
async def get_host_template(
    host_id: str, db: AsyncSession = Depends(async_get_db)  # noqa: B008
) -> TemplateHostSchema:
    """Get a host template.

    Args:
    ----
        host_id (str): Id of the host.
        db (AsyncSession): Async database connection.

    Returns:
    -------
        TemplateHostSchema: Host data from database.

    """
    if not is_valid_uuid4(host_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID provided is not a valid UUID4.",
        )

    openlabs_host = await get_host(db, TemplateHostID(id=host_id))

    if not openlabs_host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host with id: {host_id} not found!",
        )

    return TemplateHostSchema.model_validate(openlabs_host, from_attributes=True)


@router.post("/hosts")
async def upload_host_template(
    openlabs_host: TemplateHostBaseSchema,
    db: AsyncSession = Depends(async_get_db),  # noqa: B008
) -> TemplateHostID:
    """Upload a host template.

    Args:
    ----
        openlabs_host (TemplateHostBaseSchema): OpenLabs compliant host object.
        db (AsyncSession): Async database connection.

    Returns:
    -------
        TemplateHostID: Identity of the subnet template.

    """
    created_host = await create_host(db, openlabs_host)
    return TemplateHostSchema.model_validate(created_host, from_attributes=True)

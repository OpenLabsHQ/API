import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import load_only

from ..enums.workspace_roles import WorkspaceRole
from ..models.workspace_model import WorkspaceModel
from ..models.workspace_user_model import WorkspaceUserModel
from ..schemas.workspace_schema import WorkspaceCreateSchema

logger = logging.getLogger(__name__)


async def create_workspace(
    db: AsyncSession, workspace: WorkspaceCreateSchema, owner_id: int
) -> WorkspaceModel:
    """Create a new workspace.
    Args:
    ----
        db (AsyncSession): Database connection.
        workspace (WorkspaceCreateSchema): Workspace data.
        owner_id (int): ID of the user who will own this workspace.
    Returns:
    -------
        WorkspaceModel: The created workspace.
    """
    # Build the workspace dictionary with required fields
    workspace_dict = workspace.model_dump()
    workspace_dict["owner_id"] = owner_id

    # Create the model without datetime fields
    workspace_obj = WorkspaceModel(**workspace_dict)

    # Set datetime fields after instantiation
    workspace_obj.created_at = datetime.now(UTC)
    workspace_obj.updated_at = datetime.now(UTC)

    db.add(workspace_obj)
    # Flush to get the ID for the workspace
    await db.flush()

    # Add the owner as an admin of the workspace
    workspace_user = WorkspaceUserModel(
        workspace_id=workspace_obj.id,
        user_id=owner_id,
        role=WorkspaceRole.ADMIN,
        time_limit=workspace_obj.default_time_limit,
    )
    # Set datetime fields after instantiation
    workspace_user.created_at = datetime.now(UTC)
    workspace_user.updated_at = datetime.now(UTC)
    db.add(workspace_user)

    await db.commit()
    await db.refresh(workspace_obj)

    return workspace_obj


async def get_workspace(db: AsyncSession, workspace_id: int) -> WorkspaceModel | None:
    """Get a workspace by ID.
    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (int): Workspace ID.
    Returns:
    -------
        WorkspaceModel | None: The workspace if found, None otherwise.
    """
    mapped_workspace_model = inspect(WorkspaceModel)
    main_columns = [
        getattr(WorkspaceModel, attr.key)
        for attr in mapped_workspace_model.column_attrs
    ]

    stmt = (
        select(WorkspaceModel)
        .where(WorkspaceModel.id == workspace_id)
        .options(load_only(*main_columns))
    )

    result = await db.execute(stmt)
    return result.scalars().first()


async def get_workspaces_by_owner(
    db: AsyncSession, owner_id: int
) -> list[WorkspaceModel]:
    """Get all workspaces owned by a user.
    Args:
    ----
        db (AsyncSession): Database connection.
        owner_id (int): Owner ID.
    Returns:
    -------
        list[WorkspaceModel]: List of workspaces owned by the user.
    """
    stmt = select(WorkspaceModel).where(WorkspaceModel.owner_id == owner_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_workspaces_by_user(
    db: AsyncSession, user_id: int
) -> list[WorkspaceModel]:
    """Get all workspaces a user is a member of.
    Args:
    ----
        db (AsyncSession): Database connection.
        user_id (int): User ID.
    Returns:
    -------
        list[WorkspaceModel]: List of workspaces the user is a member of.
    """
    stmt = (
        select(WorkspaceModel)
        .join(WorkspaceUserModel, WorkspaceModel.id == WorkspaceUserModel.workspace_id)
        .where(WorkspaceUserModel.user_id == user_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_workspace(
    db: AsyncSession, workspace_id: int, workspace_data: dict[str, Any]
) -> WorkspaceModel | None:
    """Update a workspace.
    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (int): Workspace ID.
        workspace_data (dict[str, Any]): New workspace data.
    Returns:
    -------
        WorkspaceModel | None: The updated workspace if found, None otherwise.
    """
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        return None

    workspace_data["updated_at"] = datetime.now(UTC)

    for key, value in workspace_data.items():
        setattr(workspace, key, value)

    await db.commit()
    await db.refresh(workspace)
    return workspace


async def delete_workspace(db: AsyncSession, workspace_id: int) -> bool:
    """Delete a workspace.
    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (int): Workspace ID.
    Returns:
    -------
        bool: True if deleted, False otherwise.
    """
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        return False

    await db.delete(workspace)
    await db.commit()
    return True


async def is_workspace_owner(
    db: AsyncSession, workspace_id: int, user_id: int
) -> bool:
    """Check if a user is the owner of a workspace.
    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (int): Workspace ID.
        user_id (int): User ID.
    Returns:
    -------
        bool: True if the user is the owner, False otherwise.
    """
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        return False

    return workspace.owner_id == user_id


async def is_workspace_admin(
    db: AsyncSession, workspace_id: int, user_id: int
) -> bool:
    """Check if a user is an admin of a workspace.
    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (int): Workspace ID.
        user_id (int): User ID.
    Returns:
    -------
        bool: True if the user is an admin, False otherwise.
    """
    stmt = (
        select(WorkspaceUserModel)
        .where(WorkspaceUserModel.workspace_id == workspace_id)
        .where(WorkspaceUserModel.user_id == user_id)
        .where(WorkspaceUserModel.role == WorkspaceRole.ADMIN)
    )
    result = await db.execute(stmt)
    return result.scalars().first() is not None


async def is_workspace_member(
    db: AsyncSession, workspace_id: int, user_id: int
) -> bool:
    """Check if a user is a member of a workspace.
    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (int): Workspace ID.
        user_id (int): User ID.
    Returns:
    -------
        bool: True if the user is a member, False otherwise.
    """
    stmt = (
        select(WorkspaceUserModel)
        .where(WorkspaceUserModel.workspace_id == workspace_id)
        .where(WorkspaceUserModel.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalars().first() is not None
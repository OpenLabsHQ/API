import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from ..enums.permissions import PermissionEntityType, PermissionType
from ..models.blueprint_permission_model import BlueprintPermissionModel
from ..schemas.blueprint_permission_schema import BlueprintPermissionCreateSchema

logger = logging.getLogger(__name__)


async def create_blueprint_permission(
    db: AsyncSession, permission: BlueprintPermissionCreateSchema
) -> BlueprintPermissionModel:
    """Create a new blueprint permission.

    Args:
    ----
        db (AsyncSession): Database connection.
        permission (BlueprintPermissionCreateSchema): Permission data.

    Returns:
    -------
        BlueprintPermissionModel: The created permission.

    """
    permission_dict = permission.model_dump()

    permission_obj = BlueprintPermissionModel(**permission_dict)

    # Set datetime fields after instantiation
    permission_obj.created_at = datetime.now(UTC)
    permission_obj.updated_at = datetime.now(UTC)

    db.add(permission_obj)
    await db.commit()
    await db.refresh(permission_obj)

    return permission_obj


async def get_blueprint_permission(
    db: AsyncSession, permission_id: int
) -> BlueprintPermissionModel | None:
    """Get a blueprint permission by ID.

    Args:
    ----
        db (AsyncSession): Database connection.
        permission_id (int): Permission ID.

    Returns:
    -------
        BlueprintPermissionModel | None: The permission if found, None otherwise.

    """
    stmt = select(BlueprintPermissionModel).where(
        BlueprintPermissionModel.id == permission_id
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_blueprint_permissions_by_blueprint(
    db: AsyncSession, blueprint_type: str, blueprint_id: int
) -> list[BlueprintPermissionModel]:
    """Get all permissions for a blueprint.

    Args:
    ----
        db (AsyncSession): Database connection.
        blueprint_type (str): Type of blueprint.
        blueprint_id (int): Blueprint ID.

    Returns:
    -------
        list[BlueprintPermissionModel]: List of permissions.

    """
    stmt = (
        select(BlueprintPermissionModel)
        .where(BlueprintPermissionModel.blueprint_type == blueprint_type)
        .where(BlueprintPermissionModel.blueprint_id == blueprint_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_blueprints_by_workspace(
    db: AsyncSession, workspace_id: int
) -> list[BlueprintPermissionModel]:
    """Get all blueprints shared with a workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (int): The workspace ID.

    Returns:
    -------
        list[BlueprintPermissionModel]: List of blueprint permissions for the workspace.

    """
    stmt = (
        select(BlueprintPermissionModel)
        .where(BlueprintPermissionModel.entity_type == PermissionEntityType.WORKSPACE)
        .where(BlueprintPermissionModel.entity_id == workspace_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_workspace_blueprint_permission(
    db: AsyncSession, workspace_id: int, blueprint_type: str, blueprint_id: int
) -> BlueprintPermissionModel | None:
    """Get a specific blueprint permission for a workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (int): Workspace ID.
        blueprint_type (str): Type of blueprint.
        blueprint_id (int): Blueprint ID.

    Returns:
    -------
        BlueprintPermissionModel | None: The permission if found, None otherwise.

    """
    stmt = (
        select(BlueprintPermissionModel)
        .where(BlueprintPermissionModel.blueprint_type == blueprint_type)
        .where(BlueprintPermissionModel.blueprint_id == blueprint_id)
        .where(BlueprintPermissionModel.entity_type == PermissionEntityType.WORKSPACE)
        .where(BlueprintPermissionModel.entity_id == workspace_id)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


@dataclass
class BlueprintIdentifier:
    """Blueprint identifier with type and ID."""

    blueprint_type: str
    blueprint_id: int


@dataclass
class EntityIdentifier:
    """Entity identifier with type and ID."""

    entity_type: PermissionEntityType
    entity_id: int


async def get_user_workspaces_with_blueprint_access(
    db: AsyncSession, user_id: int, blueprint_type: str, blueprint_id: int
) -> list[int]:
    """Get all workspace IDs that the user is a member of and have access to a specific blueprint.

    Args:
    ----
        db (AsyncSession): Database connection.
        user_id (int): User ID.
        blueprint_type (str): Type of blueprint.
        blueprint_id (int): Blueprint ID.

    Returns:
    -------
        list[int]: List of workspace IDs.

    """
    # This query finds all workspaces where:
    # 1. The user is a member of the workspace
    # 2. The workspace has permission for the specified blueprint

    from sqlalchemy import and_

    from ..models.workspace_user_model import WorkspaceUserModel

    stmt = (
        select(WorkspaceUserModel.workspace_id)
        .join(
            BlueprintPermissionModel,
            and_(
                BlueprintPermissionModel.entity_type == PermissionEntityType.WORKSPACE,
                BlueprintPermissionModel.entity_id == WorkspaceUserModel.workspace_id,
                BlueprintPermissionModel.blueprint_type == blueprint_type,
                BlueprintPermissionModel.blueprint_id == blueprint_id,
            ),
            isouter=True,
        )
        .where(WorkspaceUserModel.user_id == user_id)
        .where(BlueprintPermissionModel.id.is_not(None))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def check_user_blueprint_access(
    db: AsyncSession,
    user_id: int,
    blueprint_type: str,
    blueprint_id: int,
    permission_type: PermissionType,
) -> bool:
    """Check if a user has access to a blueprint either directly or through a workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        user_id (int): User ID.
        blueprint_type (str): Type of blueprint.
        blueprint_id (int): Blueprint ID.
        permission_type (PermissionType): Type of permission required.

    Returns:
    -------
        bool: True if the user has access, False otherwise.

    """
    # Check direct user permission first
    user_permission_stmt = (
        select(BlueprintPermissionModel)
        .where(BlueprintPermissionModel.blueprint_type == blueprint_type)
        .where(BlueprintPermissionModel.blueprint_id == blueprint_id)
        .where(BlueprintPermissionModel.entity_type == PermissionEntityType.USER)
        .where(BlueprintPermissionModel.entity_id == user_id)
    )

    # For READ permission, we can accept either READ or WRITE
    # For WRITE permission, we must have WRITE specifically
    if permission_type == PermissionType.READ:
        user_permission_stmt = user_permission_stmt.where(
            BlueprintPermissionModel.permission_type.in_(
                [PermissionType.READ, PermissionType.WRITE]
            )
        )
    else:
        user_permission_stmt = user_permission_stmt.where(
            BlueprintPermissionModel.permission_type == PermissionType.WRITE
        )

    result = await db.execute(user_permission_stmt)
    user_permission = result.scalars().first()

    if user_permission:
        return True

    # If no direct permission, check workspace permissions
    workspace_ids = await get_user_workspaces_with_blueprint_access(
        db, user_id, blueprint_type, blueprint_id
    )
    return len(workspace_ids) > 0


async def sync_workspace_blueprint_permissions(
    db: AsyncSession, workspace_id: int
) -> None:
    """Sync blueprint permissions for all users in a workspace.

    When a blueprint is shared with a workspace, ensure all users in the workspace
    have access to all blueprints shared with the workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        workspace_id (int): Workspace ID.

    """
    # Import here to avoid circular imports
    from ..models.workspace_user_model import WorkspaceUserModel

    # Get all users in the workspace
    users_stmt = select(WorkspaceUserModel.user_id).where(
        WorkspaceUserModel.workspace_id == workspace_id
    )
    users_result = await db.execute(users_stmt)
    user_ids = users_result.scalars().all()

    # Get all blueprints shared with the workspace
    blueprints_stmt = select(BlueprintPermissionModel).where(
        BlueprintPermissionModel.entity_type == PermissionEntityType.WORKSPACE,
        BlueprintPermissionModel.entity_id == workspace_id,
    )
    blueprints_result = await db.execute(blueprints_stmt)
    blueprint_permissions = blueprints_result.scalars().all()

    # For each user and blueprint, ensure the user has access
    for user_id in user_ids:
        for blueprint_permission in blueprint_permissions:
            # Check if user already has direct permission to this blueprint
            existing_stmt = (
                select(BlueprintPermissionModel)
                .where(
                    BlueprintPermissionModel.blueprint_type
                    == blueprint_permission.blueprint_type
                )
                .where(
                    BlueprintPermissionModel.blueprint_id
                    == blueprint_permission.blueprint_id
                )
                .where(BlueprintPermissionModel.entity_type == PermissionEntityType.USER)
                .where(BlueprintPermissionModel.entity_id == user_id)
            )
            existing_result = await db.execute(existing_stmt)
            existing_permission = existing_result.scalars().first()

            # Skip if user already has direct permission
            if existing_permission:
                continue

            # Create permission for the user
            new_permission = BlueprintPermissionModel(
                blueprint_type=blueprint_permission.blueprint_type,
                blueprint_id=blueprint_permission.blueprint_id,
                entity_type=PermissionEntityType.USER,
                entity_id=user_id,
                permission_type=blueprint_permission.permission_type,
            )

            # Set datetime fields after instantiation
            new_permission.created_at = datetime.now(UTC)
            new_permission.updated_at = datetime.now(UTC)

            db.add(new_permission)

    # Commit all changes at once
    await db.commit()


async def sync_user_workspace_permissions(
    db: AsyncSession, user_id: int, workspace_id: int
) -> None:
    """Sync blueprint permissions for a user added to a workspace.

    When a user is added to a workspace, ensure they have access to all blueprints
    shared with the workspace.

    Args:
    ----
        db (AsyncSession): Database connection.
        user_id (int): User ID.
        workspace_id (int): Workspace ID.

    """
    # Get all blueprints shared with the workspace
    blueprints_stmt = select(BlueprintPermissionModel).where(
        BlueprintPermissionModel.entity_type == PermissionEntityType.WORKSPACE,
        BlueprintPermissionModel.entity_id == workspace_id,
    )
    blueprints_result = await db.execute(blueprints_stmt)
    blueprint_permissions = blueprints_result.scalars().all()

    # For each blueprint, ensure the user has access
    for blueprint_permission in blueprint_permissions:
        # Check if user already has direct permission to this blueprint
        existing_stmt = (
            select(BlueprintPermissionModel)
            .where(
                BlueprintPermissionModel.blueprint_type
                == blueprint_permission.blueprint_type
            )
            .where(
                BlueprintPermissionModel.blueprint_id == blueprint_permission.blueprint_id
            )
            .where(BlueprintPermissionModel.entity_type == PermissionEntityType.USER)
            .where(BlueprintPermissionModel.entity_id == user_id)
        )
        existing_result = await db.execute(existing_stmt)
        existing_permission = existing_result.scalars().first()

        # Skip if user already has direct permission
        if existing_permission:
            continue

        # Create permission for the user
        new_permission = BlueprintPermissionModel(
            blueprint_type=blueprint_permission.blueprint_type,
            blueprint_id=blueprint_permission.blueprint_id,
            entity_type=PermissionEntityType.USER,
            entity_id=user_id,
            permission_type=blueprint_permission.permission_type,
        )

        # Set datetime fields after instantiation
        new_permission.created_at = datetime.now(UTC)
        new_permission.updated_at = datetime.now(UTC)

        db.add(new_permission)

    # Commit all changes at once
    await db.commit()


async def delete_blueprint_permission(db: AsyncSession, permission_id: int) -> bool:
    """Delete a blueprint permission.

    Args:
    ----
        db (AsyncSession): Database connection.
        permission_id (int): Permission ID.

    Returns:
    -------
        bool: True if deleted, False otherwise.

    """
    permission = await get_blueprint_permission(db, permission_id)
    if not permission:
        return False

    await db.delete(permission)
    await db.commit()
    return True

import logging
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio.session import AsyncSession

from ...core.auth.auth import get_current_user
from ...core.db.database import async_get_db
from ...crud.crud_blueprint_permissions import (
    create_blueprint_permission,
    delete_blueprint_permission,
    get_blueprints_by_workspace,
    get_workspace_blueprint_permission,
    sync_user_workspace_permissions,
    sync_workspace_blueprint_permissions,
)
from ...crud.crud_workspace_users import (
    add_user_to_workspace,
    get_workspace_users_with_details,
    remove_user_from_workspace,
    update_workspace_user,
)
from ...crud.crud_workspaces import (
    create_workspace,
    delete_workspace,
    get_workspace,
    get_workspaces_by_owner,
    get_workspaces_by_user,
    is_workspace_admin,
    is_workspace_member,
    is_workspace_owner,
    update_workspace,
)
from ...enums.permissions import PermissionEntityType
from ...models.user_model import UserModel
from ...schemas.message_schema import MessageSchema
from ...schemas.blueprint_permission_schema import (
    BlueprintPermissionCreateSchema,
    BlueprintPermissionSchema,
)
from ...schemas.workspace_schema import (
    WorkspaceCreateSchema,
    WorkspaceSchema,
    WorkspaceBlueprintDeleteSchema,
    WorkspaceBlueprintSchema,
)
from ...schemas.workspace_user_schema import (
    WorkspaceUserCreateSchema,
    WorkspaceUserDetailSchema,
    WorkspaceUserSchema,
    WorkspaceUserUpdateSchema,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
logger = logging.getLogger(__name__)


@router.post("", response_model=WorkspaceSchema, status_code=status.HTTP_201_CREATED)
async def create_new_workspace(
    workspace: WorkspaceCreateSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> WorkspaceSchema:
    """Create a new workspace.

    Args:
    ----
        workspace (WorkspaceCreateSchema): The workspace data.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        WorkspaceModel: The created workspace.

    """
    workspace_model = await create_workspace(db, workspace, current_user.id)
    # Convert to schema for proper response serialization
    return WorkspaceSchema(
        id=workspace_model.id,
        name=workspace_model.name,
        description=workspace_model.description,
        default_time_limit=workspace_model.default_time_limit,
        owner_id=workspace_model.owner_id,
        created_at=workspace_model.created_at.isoformat(),
        updated_at=workspace_model.updated_at.isoformat(),
    )


@router.get("", response_model=list[WorkspaceSchema])
async def get_workspaces(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> list[WorkspaceSchema]:
    """Get all workspaces the user has access to.

    Args:
    ----
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        list[WorkspaceModel]: The workspaces the user has access to.

    """
    # Admins can see all workspaces they own
    if current_user.is_admin:
        workspace_models = await get_workspaces_by_owner(db, current_user.id)
    else:
        # Regular users see workspaces they are members of
        workspace_models = await get_workspaces_by_user(db, current_user.id)

    # Convert models to schemas for response serialization
    return [
        WorkspaceSchema(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            default_time_limit=workspace.default_time_limit,
            owner_id=workspace.owner_id,
            created_at=workspace.created_at.isoformat(),
            updated_at=workspace.updated_at.isoformat(),
        )
        for workspace in workspace_models
    ]


@router.get("/{workspace_id}", response_model=WorkspaceSchema)
async def get_workspace_by_id(
    workspace_id: int = Path(..., description="The ID of the workspace to get"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> WorkspaceSchema:
    """Get a workspace by ID.

    Args:
    ----
        workspace_id (int): The ID of the workspace to get.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        WorkspaceModel: The workspace.

    """
    workspace_model = await get_workspace(db, workspace_id)
    if not workspace_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user has access to the workspace
    if not current_user.is_admin and not await is_workspace_member(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace",
        )

    # Convert model to schema for response serialization
    return WorkspaceSchema(
        id=workspace_model.id,
        name=workspace_model.name,
        description=workspace_model.description,
        default_time_limit=workspace_model.default_time_limit,
        owner_id=workspace_model.owner_id,
        created_at=workspace_model.created_at.isoformat(),
        updated_at=workspace_model.updated_at.isoformat(),
    )


@router.put("/{workspace_id}", response_model=WorkspaceSchema)
async def update_workspace_by_id(
    workspace_data: WorkspaceCreateSchema,
    workspace_id: int = Path(..., description="The ID of the workspace to update"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> WorkspaceSchema:
    """Update a workspace.

    Args:
    ----
        workspace_data (WorkspaceCreateSchema): The new workspace data.
        workspace_id (int): The ID of the workspace to update.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        WorkspaceModel: The updated workspace.

    """
    # Check if workspace exists
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is authorized to update workspace
    if not current_user.is_admin and not await is_workspace_admin(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this workspace",
        )

    # Update workspace
    updated_workspace = await update_workspace(
        db, workspace_id, workspace_data.model_dump()
    )
    if not updated_workspace:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workspace",
        )

    # Convert model to schema for response serialization
    return WorkspaceSchema(
        id=updated_workspace.id,
        name=updated_workspace.name,
        description=updated_workspace.description,
        default_time_limit=updated_workspace.default_time_limit,
        owner_id=updated_workspace.owner_id,
        created_at=updated_workspace.created_at.isoformat(),
        updated_at=updated_workspace.updated_at.isoformat(),
    )


@router.delete("/{workspace_id}", response_model=MessageSchema)
async def delete_workspace_by_id(
    workspace_id: int = Path(..., description="The ID of the workspace to delete"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> MessageSchema:
    """Delete a workspace.

    Args:
    ----
        workspace_id (int): The ID of the workspace to delete.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        MessageSchema: Success message.

    """
    # Check if user is authorized to delete workspace
    if not current_user.is_admin and not await is_workspace_owner(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this workspace",
        )

    # First, clean up all blueprint permissions related to this workspace
    from sqlalchemy import delete

    from ...models.blueprint_permission_model import BlueprintPermissionModel

    # 1. Find all blueprints shared with the workspace
    workspace_blueprints = await get_blueprints_by_workspace(db, workspace_id)

    # 2. Delete all blueprint permissions for the workspace itself
    workspace_perms_stmt = (
        delete(BlueprintPermissionModel)
        .where(BlueprintPermissionModel.entity_type == PermissionEntityType.WORKSPACE)
        .where(BlueprintPermissionModel.entity_id == workspace_id)
    )
    await db.execute(workspace_perms_stmt)

    # 3. Get all users in the workspace to clean up their permissions
    from ...crud.crud_workspace_users import get_workspace_users

    workspace_users = await get_workspace_users(db, workspace_id)
    user_ids = [user.user_id for user in workspace_users]

    # 4. For each blueprint that was shared with the workspace, delete permissions
    # for users who were part of this workspace
    for blueprint_perm in workspace_blueprints:
        for user_id in user_ids:
            # Find and delete user permissions for these blueprints
            user_perm_stmt = (
                delete(BlueprintPermissionModel)
                .where(
                    BlueprintPermissionModel.blueprint_type == blueprint_perm.blueprint_type
                )
                .where(BlueprintPermissionModel.blueprint_id == blueprint_perm.blueprint_id)
                .where(BlueprintPermissionModel.entity_type == PermissionEntityType.USER)
                .where(BlueprintPermissionModel.entity_id == user_id)
            )
            await db.execute(user_perm_stmt)

    # Commit all permission deletions
    await db.commit()

    # Finally, delete the workspace
    success = await delete_workspace(db, workspace_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    return MessageSchema(message="Workspace deleted successfully")


@router.get("/{workspace_id}/users", response_model=list[WorkspaceUserDetailSchema])
async def get_workspace_users_by_workspace_id(
    workspace_id: int = Path(..., description="The ID of the workspace"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> list[WorkspaceUserDetailSchema]:
    """Get all users in a workspace with their details.

    Args:
    ----
        workspace_id (int): The ID of the workspace.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        list[WorkspaceUserDetailSchema]: The users in the workspace with their details.

    """
    # Check if workspace exists
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is authorized to view workspace users
    if not current_user.is_admin and not await is_workspace_member(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace",
        )

    # Get workspace users with their user details
    workspace_users_with_details = await get_workspace_users_with_details(
        db, workspace_id
    )

    # Convert models to schemas with properly formatted dates and user details
    return [
        WorkspaceUserDetailSchema(
            workspace_id=workspace_user.workspace_id,
            user_id=workspace_user.user_id,
            role=workspace_user.role,
            time_limit=workspace_user.time_limit,
            created_at=workspace_user.created_at.isoformat(),
            updated_at=workspace_user.updated_at.isoformat(),
            name=user_details.name,
            email=user_details.email,
        )
        for workspace_user, user_details in workspace_users_with_details
    ]


@router.post("/{workspace_id}/users", response_model=WorkspaceUserSchema)
async def add_user_to_workspace_by_id(
    user_data: WorkspaceUserCreateSchema,
    workspace_id: int = Path(..., description="The ID of the workspace"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> WorkspaceUserSchema:
    """Add a user to a workspace.

    Args:
    ----
        user_data (WorkspaceUserCreateSchema): The user data.
        workspace_id (int): The ID of the workspace.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        WorkspaceUserSchema: The created workspace user association.

    """
    # Check if user is authorized to add users to workspace
    if not current_user.is_admin and not await is_workspace_admin(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to add users to this workspace",
        )

    # Add user to workspace
    workspace_user = await add_user_to_workspace(db, workspace_id, user_data)
    if not workspace_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace or user not found",
        )

    # Sync blueprint permissions for the new user
    try:
        # First sync workspace permissions for this user
        await sync_user_workspace_permissions(db, user_data.user_id, workspace_id)
        
        # Then sync all user permissions in the workspace to ensure consistency
        await sync_workspace_blueprint_permissions(db, workspace_id)
        
        logger.info(f"Successfully synced permissions for user {user_data.user_id} in workspace {workspace_id}")
    except Exception as e:
        logger.error(f"Error syncing permissions for user {user_data.user_id} in workspace {workspace_id}: {e}")

    # Convert model to schema with properly formatted dates
    return WorkspaceUserSchema(
        workspace_id=workspace_user.workspace_id,
        user_id=workspace_user.user_id,
        role=workspace_user.role,
        time_limit=workspace_user.time_limit,
        created_at=workspace_user.created_at.isoformat(),
        updated_at=workspace_user.updated_at.isoformat(),
    )


@router.delete("/{workspace_id}/users/{user_id}", response_model=MessageSchema)
async def remove_user_from_workspace_by_id(
    workspace_id: int = Path(..., description="The ID of the workspace"),
    user_id: int = Path(..., description="The ID of the user to remove"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> MessageSchema:
    """Remove a user from a workspace.

    Args:
    ----
        workspace_id (int): The ID of the workspace.
        user_id (int): The ID of the user to remove.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        MessageSchema: Success message.

    """
    # Check if user is authorized to remove users from workspace
    if not current_user.is_admin and not await is_workspace_admin(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to remove users from this workspace",
        )

    # Check if user is trying to remove themselves
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove yourself from the workspace",
        )

    # Check if user is trying to remove the workspace owner
    workspace = await get_workspace(db, workspace_id)
    if workspace and workspace.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove the workspace owner",
        )

    # First check if the user is in the workspace to avoid unnecessary operations
    user_in_workspace = await remove_user_from_workspace(db, workspace_id, user_id)
    if not user_in_workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in workspace",
        )

    # After removing the user from workspace, also clean up their blueprint permissions
    # that were granted through this workspace membership

    # 1. Get all blueprints shared with the workspace
    workspace_blueprints = await get_blueprints_by_workspace(db, workspace_id)

    if workspace_blueprints:
        # 2. For each blueprint, check if the user has a direct permission that was
        # granted through workspace membership and remove it
        from sqlalchemy import and_, delete

        from ...models.blueprint_permission_model import BlueprintPermissionModel

        for blueprint_perm in workspace_blueprints:
            # Delete any user permission for this blueprint
            stmt = delete(BlueprintPermissionModel).where(
                and_(
                    BlueprintPermissionModel.blueprint_type
                    == blueprint_perm.blueprint_type,
                    BlueprintPermissionModel.blueprint_id == blueprint_perm.blueprint_id,
                    BlueprintPermissionModel.entity_type == PermissionEntityType.USER,
                    BlueprintPermissionModel.entity_id == user_id,
                )
            )
            await db.execute(stmt)

        # Commit all the deletions
        await db.commit()

    return MessageSchema(message="User removed from workspace successfully")


@router.put("/{workspace_id}/users/{user_id}", response_model=WorkspaceUserSchema)
async def update_workspace_user_role(
    user_data: WorkspaceUserUpdateSchema,
    workspace_id: int = Path(..., description="The ID of the workspace"),
    user_id: int = Path(..., description="The ID of the user to update"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> WorkspaceUserSchema:
    """Update a user's role or time limit in a workspace.

    Args:
    ----
        user_data (WorkspaceUserUpdateSchema): The updated user data.
        workspace_id (int): The ID of the workspace.
        user_id (int): The ID of the user to update.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        WorkspaceUserSchema: The updated workspace user association.

    """
    # Check if workspace exists
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is authorized to update users in this workspace
    if not current_user.is_admin and not await is_workspace_admin(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update users in this workspace",
        )

    # Check if trying to update the workspace owner's role (not allowed)
    if workspace.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change the workspace owner's role",
        )

    # Update the user's role and/or time limit
    update_data = user_data.model_dump(exclude_unset=True)
    updated_user = await update_workspace_user(db, workspace_id, user_id, update_data)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in workspace",
        )

    return WorkspaceUserSchema(
        workspace_id=updated_user.workspace_id,
        user_id=updated_user.user_id,
        role=updated_user.role,
        time_limit=updated_user.time_limit,
        created_at=updated_user.created_at.isoformat(),
        updated_at=updated_user.updated_at.isoformat(),
    )


@router.get("/{workspace_id}/blueprints", response_model=list[BlueprintPermissionSchema])
async def get_workspace_blueprints(
    workspace_id: int = Path(..., description="The ID of the workspace"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> list[BlueprintPermissionSchema]:
    """Get all blueprints shared with a workspace.

    Args:
    ----
        workspace_id (int): The ID of the workspace.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        list[BlueprintPermissionSchema]: The blueprints shared with the workspace.

    """
    # Check if workspace exists
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is authorized to view workspace blueprints
    if not current_user.is_admin and not await is_workspace_member(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace",
        )

    # Get all blueprints shared with the workspace
    blueprint_permissions = await get_blueprints_by_workspace(db, workspace_id)

    # Convert to response schema
    return [
        BlueprintPermissionSchema(
            id=permission.id,
            blueprint_type=permission.blueprint_type,
            blueprint_id=permission.blueprint_id,
            entity_type=permission.entity_type,
            entity_id=permission.entity_id,
            permission_type=permission.permission_type,
            created_at=permission.created_at.isoformat(),
            updated_at=permission.updated_at.isoformat(),
        )
        for permission in blueprint_permissions
    ]


@router.post(
    "/{workspace_id}/blueprints",
    response_model=BlueprintPermissionSchema,
    status_code=status.HTTP_201_CREATED,
)
async def share_blueprint_with_workspace(
    blueprint_data: WorkspaceBlueprintSchema,
    workspace_id: int = Path(..., description="The ID of the workspace"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> BlueprintPermissionSchema:
    """Share a blueprint with a workspace.

    Args:
    ----
        blueprint_data (WorkspaceBlueprintSchema): The blueprint data.
        workspace_id (int): The ID of the workspace.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        BlueprintPermissionSchema: The created blueprint permission.

    """
    # Check if workspace exists
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is authorized to share blueprints with the workspace
    if not current_user.is_admin and not await is_workspace_admin(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to share blueprints with this workspace",
        )

    # Build the blueprint permission
    permission_data = BlueprintPermissionCreateSchema(
        blueprint_type=blueprint_data.blueprint_type,
        blueprint_id=blueprint_data.blueprint_id,
        entity_type=PermissionEntityType.WORKSPACE,
        entity_id=workspace_id,
        permission_type=blueprint_data.permission_type,
    )

    # Create the permission for the workspace
    created_permission = await create_blueprint_permission(db, permission_data)

    # Sync permissions for all users in the workspace
    try:
        # First sync all workspace users' permissions
        await sync_workspace_blueprint_permissions(db, workspace_id)
        
        logger.info(f"Successfully synced permissions for blueprint {blueprint_data.blueprint_id} in workspace {workspace_id}")
    except Exception as e:
        logger.error(f"Error syncing permissions for workspace {workspace_id}: {e}")
        # Even if sync fails, proceed with returning the created permission

    # Return the created permission
    return BlueprintPermissionSchema(
        id=created_permission.id,
        blueprint_type=created_permission.blueprint_type,
        blueprint_id=created_permission.blueprint_id,
        entity_type=created_permission.entity_type,
        entity_id=created_permission.entity_id,
        permission_type=created_permission.permission_type,
        created_at=created_permission.created_at.isoformat(),
        updated_at=created_permission.updated_at.isoformat(),
    )


@router.delete(
    "/{workspace_id}/blueprints/{blueprint_id}",
    response_model=WorkspaceBlueprintDeleteSchema,
)
async def remove_blueprint_from_workspace(
    workspace_id: int = Path(..., description="The ID of the workspace"),
    blueprint_id: int = Path(..., description="The ID of the blueprint"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> WorkspaceBlueprintDeleteSchema:
    """Remove a blueprint from a workspace.

    Args:
    ----
        workspace_id (int): The ID of the workspace.
        blueprint_id (int): The ID of the blueprint.
        current_user (UserModel): The authenticated user.
        db (AsyncSession): Database connection.

    Returns:
    -------
        WorkspaceBlueprintDeleteSchema: Success message.

    """
    # Check if workspace exists
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Check if user is authorized to remove blueprints from the workspace
    if not current_user.is_admin and not await is_workspace_admin(
        db, workspace_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to remove blueprints from this workspace",
        )

    # Find any blueprint permission for this workspace and blueprint
    # Try all blueprint types until we find a match
    blueprint_types = [
        "range_blueprints",
        "vpc_blueprints",
        "subnet_blueprints",
        "host_blueprints",
    ]
    permission = None

    for blueprint_type in blueprint_types:
        permission = await get_workspace_blueprint_permission(
            db, workspace_id, blueprint_type, blueprint_id
        )
        if permission:
            break

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blueprint is not shared with this workspace",
        )

    # Capture the blueprint details before deletion
    blueprint_type = permission.blueprint_type
    blueprint_id = permission.blueprint_id

    # Delete the workspace permission
    success = await delete_blueprint_permission(db, permission.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove blueprint from workspace",
        )

    # Also delete any derived user permissions for this blueprint
    # that were created automatically through workspace membership
    from sqlalchemy import select

    from ...models.blueprint_permission_model import BlueprintPermissionModel
    from ...models.workspace_user_model import WorkspaceUserModel

    # Get all users in the workspace
    users_stmt = select(WorkspaceUserModel.user_id).where(
        WorkspaceUserModel.workspace_id == workspace_id
    )
    users_result = await db.execute(users_stmt)
    user_ids = users_result.scalars().all()

    # For each user, delete corresponding blueprint permissions
    for user_id in user_ids:
        # Find the user's permission for this blueprint
        stmt = (
            select(BlueprintPermissionModel)
            .where(BlueprintPermissionModel.blueprint_type == blueprint_type)
            .where(BlueprintPermissionModel.blueprint_id == blueprint_id)
            .where(BlueprintPermissionModel.entity_type == PermissionEntityType.USER)
            .where(BlueprintPermissionModel.entity_id == user_id)
        )
        result = await db.execute(stmt)
        user_permission = result.scalars().first()

        # Delete the user permission if found
        if user_permission:
            await db.delete(user_permission)

    # Commit all the deletions
    await db.commit()

    # Return success message
    return WorkspaceBlueprintDeleteSchema(success=True)



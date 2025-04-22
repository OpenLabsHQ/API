from pydantic import BaseModel, ConfigDict, Field

from ..enums.workspace_roles import WorkspaceRole


class WorkspaceUserBaseSchema(BaseModel):
    """Base schema for workspace user association."""

    user_id: int = Field(
        ...,
        description="ID of the user being added to the workspace",
    )
    workspace_id: int = Field(
        ...,
        description="ID of the workspace the user is being added to",
    )
    role: WorkspaceRole = Field(
        WorkspaceRole.MEMBER,
        description="Role of the user in the workspace",
    )
    time_limit: int = Field(
        ...,
        description="Time limit for this user in seconds",
        examples=[3600, 7200, 86400],
        ge=1,  # Must be at least 1 second
    )


class WorkspaceUserSchema(WorkspaceUserBaseSchema):
    """Schema for complete workspace user data."""

    created_at: str = Field(
        ..., description="Timestamp when the user was added to the workspace"
    )
    updated_at: str = Field(
        ..., description="Timestamp when the user's workspace data was last updated"
    )

    model_config = ConfigDict(from_attributes=True)


class WorkspaceUserDetailSchema(WorkspaceUserSchema):
    """Schema for workspace user data with detailed user information."""

    name: str = Field(
        ...,
        description="Full name of the user",
    )
    email: str = Field(
        ...,
        description="Email of the user",
    )

    model_config = ConfigDict(from_attributes=True)


class WorkspaceUserCreateSchema(BaseModel):
    """Schema for adding a user to a workspace."""

    user_id: int = Field(
        ...,
        description="ID of the user to add to the workspace",
    )
    role: WorkspaceRole = Field(
        WorkspaceRole.MEMBER,
        description="Role of the user in the workspace",
    )
    time_limit: int | None = Field(
        None,
        description="Optional time limit override for this user in seconds",
        examples=[3600, 7200, 86400],
        ge=1,  # Must be at least 1 second
    )

    model_config = ConfigDict(from_attributes=True)


class WorkspaceUserUpdateSchema(BaseModel):
    """Schema for updating a user's role in a workspace."""

    role: WorkspaceRole = Field(
        ...,
        description="New role for the user in the workspace",
    )
    time_limit: int | None = Field(
        None,
        description="Optional new time limit for this user in seconds",
        examples=[3600, 7200, 86400],
        ge=1,  # Must be at least 1 second
    )

    model_config = ConfigDict(from_attributes=True)

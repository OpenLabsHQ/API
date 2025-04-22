from pydantic import BaseModel, ConfigDict, Field

from ..enums.permissions import PermissionType


class WorkspaceBaseSchema(BaseModel):
    """Base schema for workspace data."""

    name: str = Field(
        ...,
        description="Name of the workspace",
        min_length=3,
        max_length=50,
        examples=["Blue Team", "Security Team"],
    )
    description: str | None = Field(
        None,
        description="Description of the workspace",
        max_length=500,
        examples=["Workspace for the Blue Team"],
    )
    default_time_limit: int = Field(
        3600,
        description="Default time limit for workspace users in seconds",
        examples=[3600, 7200, 86400],
        ge=1,  # Must be at least 1 second
    )


class WorkspaceID(BaseModel):
    """Identity class for Workspace."""

    id: int = Field(
        description="Unique workspace identifier."
    )

    model_config = ConfigDict(from_attributes=True)


class WorkspaceSchema(WorkspaceBaseSchema, WorkspaceID):
    """Schema for complete workspace data including ID."""

    owner_id: int = Field(
        ..., description="ID of the user who owns this workspace"
    )
    created_at: str = Field(..., description="Timestamp when the workspace was created")
    updated_at: str = Field(
        ..., description="Timestamp when the workspace was last updated"
    )

    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreateSchema(WorkspaceBaseSchema):
    """Schema for creating a new workspace."""

    model_config = ConfigDict(from_attributes=True)


class WorkspaceBlueprintSchema(BaseModel):
    """Schema for assigning a blueprint to a workspace."""

    blueprint_id: int = Field(
        ...,
        description="ID of the blueprint to share with the workspace",
    )
    blueprint_type: str = Field(
        "range_blueprints",
        description="Type of blueprint (range, vpc, subnet, host)",
        examples=[
            "range_blueprints",
            "vpc_blueprints", 
            "subnet_blueprints",
            "host_blueprints",
        ],
    )
    permission_type: PermissionType = Field(
        PermissionType.READ,
        description="Type of permission (read or write)",
    )

    model_config = ConfigDict(from_attributes=True)


class WorkspaceBlueprintDeleteSchema(BaseModel):
    """Schema for success message after Blueprint deletion."""

    success: bool = Field(
        True,
        description="Whether the operation was successful",
    )

    model_config = ConfigDict(from_attributes=True)

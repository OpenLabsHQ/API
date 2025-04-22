from pydantic import BaseModel, ConfigDict, Field

from ..enums.permissions import PermissionEntityType, PermissionType


class BlueprintPermissionBaseSchema(BaseModel):
    """Base schema for blueprint permission."""

    blueprint_type: str = Field(
        ...,
        description="Type of blueprint (range, vpc, subnet, host)",
        examples=[
            "range_blueprints",
            "vpc_blueprints",
            "subnet_blueprints",
            "host_blueprints",
        ],
    )
    blueprint_id: int = Field(
        ...,
        description="ID of the blueprint",
    )
    entity_type: PermissionEntityType = Field(
        ...,
        description="Type of entity (user or workspace)",
    )
    entity_id: int = Field(
        ...,
        description="ID of the entity",
    )
    permission_type: PermissionType = Field(
        ...,
        description="Type of permission (read or write)",
    )


class BlueprintPermissionID(BaseModel):
    """Identity class for BlueprintPermission."""

    id: int = Field(
        description="Unique blueprint permission identifier."
    )

    model_config = ConfigDict(from_attributes=True)


class BlueprintPermissionSchema(BlueprintPermissionBaseSchema, BlueprintPermissionID):
    """Schema for complete blueprint permission data including ID."""

    created_at: str = Field(
        ..., description="Timestamp when the permission was created"
    )
    updated_at: str = Field(
        ..., description="Timestamp when the permission was last updated"
    )

    model_config = ConfigDict(from_attributes=True)


class BlueprintPermissionCreateSchema(BlueprintPermissionBaseSchema):
    """Schema for creating a new blueprint permission."""

    model_config = ConfigDict(from_attributes=True)

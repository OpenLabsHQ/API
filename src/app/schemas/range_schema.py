import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..enums.range_states import RangeState
from ..enums.regions import OpenLabsRegion


class RangeBaseSchema(BaseModel):
    """Deployed base range schema."""

    name: str = Field(..., description="Range name", min_length=1, examples=["range-1"])
    description: str = Field(
        ..., description="Description of range", examples=["This is my test range."]
    )
    date: datetime = Field(
        description="Time range was created",
        examples=[datetime(2025, 2, 5, tzinfo=timezone.utc)],
    )
    template: dict[str, Any] = Field(
        ..., description="Range template JSON string"
    )  # Dictionary not TemplateRange object to store JSON
    readme: str | None = Field(default=None, description="Markdown readme for range")
    state_file: dict[str, Any] = Field(..., description="Terraform state file")
    state: RangeState = Field(
        ...,
        description="State of deployed range",
        examples=[RangeState.ON, RangeState.OFF, RangeState.START],
    )
    region: OpenLabsRegion = Field(
        ..., description="Cloud region to deploy template range"
    )


class DeployRangeBaseSchema(BaseModel):
    """Deploy range to cloud provider schema."""

    name: str = Field(..., description="Range name", min_length=1, examples=["range-1"])
    description: str = Field(
        ..., description="Description of range", examples=["This is my test range."]
    )
    template_id: uuid.UUID = Field(..., description="Template range ID")
    region: OpenLabsRegion = Field(
        ..., description="Cloud region to deploy template range"
    )
    readme: str | None = Field(default=None, description="Markdown readme for range")


class RangeID(BaseModel):
    """Identity class for the template range object."""

    id: uuid.UUID = Field(..., description="Unique range identifier.")
    model_config = ConfigDict(from_attributes=True)


class RangeSchema(RangeBaseSchema, RangeID):
    """Deployed range schema."""

    model_config = ConfigDict(from_attributes=True)

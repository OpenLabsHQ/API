import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..enums.operating_systems import OpenLabsOS
from ..enums.specs import OpenLabsSpec
from ..validators.network import is_valid_disk_size, is_valid_hostname


class OpenLabsHostBaseSchema(BaseModel):
    """Base host object for OpenLabs."""

    hostname: str = Field(
        ...,
        description="Hostname of machine",
        min_length=1,
        examples=["example-host-1"],
    )
    os: OpenLabsOS = Field(
        ...,
        description="Operating system of machine",
        examples=[OpenLabsOS.DEBIAN_11, OpenLabsOS.KALI, OpenLabsOS.WINDOWS_2022],
    )
    spec: OpenLabsSpec = Field(
        ...,
        description="Ram and CPU size",
        examples=[OpenLabsSpec.TINY, OpenLabsSpec.SMALL],
    )
    size: int = Field(..., description="Size in GB of disk", gt=0)
    tags: list[str] = Field(
        default_factory=list,
        description="Optional list of tags",
        examples=[["web", "linux"]],
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, tags: list[str]) -> list[str]:
        """Validate no empty tags.

        Args:
        ----
            cls: Host object.
            tags (list[str]): List of tags.

        Returns:
        -------
            list[str]: List of non-empty tags.

        """
        if any(tag.strip() == "" for tag in tags):
            msg = "Tags must not be empty"
            raise ValueError(msg)
        return tags

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, hostname: str) -> str:
        """Check VM hostname is conforms to RFC1035.

        Args:
        ----
            cls: Host object.
            hostname (str): Hostname of VM.

        Returns:
        -------
            str: Valid hostname for VM.

        """
        if not is_valid_hostname(hostname):
            msg = f"Invalid hostname: {hostname}"
            raise ValueError(msg)
        return hostname

    @model_validator(mode="after")
    @classmethod
    def validate_size(cls, model: BaseModel) -> BaseModel:
        """Check VM disk size is sufficient.

        Args:
        ----
            cls: Host object.
            model (BaseModel): Host model

        Returns:
        -------
            BaseModel: Valid model for VM.

        """
        if not is_valid_disk_size(model.os, model.size):
            msg = f"Invalid disk size for {model.os.value}: {model.size}GB"
            raise ValueError(msg)
        return model


class OpenLabsHostID(BaseModel):
    """Identity class for OpenLabsHost."""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, description="Unique object identifier."
    )

    model_config = ConfigDict(from_attributes=True)


class OpenLabsHostSchema(OpenLabsHostBaseSchema, OpenLabsHostID):
    """Host object for OpenLabs."""

    model_config = ConfigDict(from_attributes=True)

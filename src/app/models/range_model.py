from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base
from ..enums.range_states import RangeState
from ..enums.regions import OpenLabsRegion
from .template_base_model import OwnableObjectMixin


class RangeModel(Base, OwnableObjectMixin):
    """Range model class."""

    __tablename__ = "ranges"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    template: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    readme: Mapped[str] = mapped_column(String, nullable=True)
    state_file: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    state: Mapped[RangeState] = mapped_column(Enum(RangeState), nullable=False)
    region: Mapped[OpenLabsRegion] = mapped_column(Enum(OpenLabsRegion), nullable=False)

    # hosts: list[CdktfBaseHost]
    # subets: list[CdktfBaseSubnet]
    # vpcs: list[CdktfBaseVPC]
    # Cloud account id for referencing specifc set of secrets - only when we allow users to store multiple set of creds for each cloud provider


# deployed_range_obj = DeployedRange(deployed_range_id, range_template, state_file, range_template.provider, account: OpenLabsAccount, cloud_account_id: uuid/int)
# OpenLabsAccount --> Provider --> Cloud Account ID --> AWS Creds

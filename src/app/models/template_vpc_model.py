import uuid
from ipaddress import IPv4Network

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import CIDR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .template_base_model import OwnableObjectMixin


class TemplateVPCModel(Base, OwnableObjectMixin):
    """SQLAlchemy ORM model for template vpc objects."""

    __tablename__ = "vpc_templates"

    name: Mapped[str] = mapped_column(String, nullable=False)
    cidr: Mapped[IPv4Network] = mapped_column(CIDR, nullable=False)

    # ForeignKey to ensure each VPC belongs to exactly one Range
    range_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("range_templates.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )

    # Relationship with Range
    range = relationship("TemplateRangeModel", back_populates="vpcs")

    # One-to-many relationship with Subnets
    subnets = relationship(
        "TemplateSubnetModel", back_populates="vpc", cascade="all, delete-orphan"
    )

    def is_standalone(self) -> bool:
        """Return whether vpc template model is a standalone model.

        Standalone means that the template is not part of a larger template.

        Returns
        -------
            bool: True if standalone. False otherwise.

        """
        return self.range_id is None

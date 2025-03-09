import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import CIDR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .template_base_model import OwnableObjectMixin


class TemplateSubnetModel(Base, OwnableObjectMixin):
    """SQLAlchemy ORM model for template subnet objects."""

    __tablename__ = "subnet_templates"

    name: Mapped[str] = mapped_column(String, nullable=False)
    cidr: Mapped[uuid.UUID] = mapped_column(CIDR, nullable=False)

    # ForeignKey to ensure each Subnet belongs to exactly one VPC
    vpc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vpc_templates.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )

    # Relationship with VPC
    vpc = relationship("TemplateVPCModel", back_populates="subnets")

    # One-to-many relationship with Hosts
    hosts = relationship(
        "TemplateHostModel", back_populates="subnet", cascade="all, delete-orphan"
    )

    def is_standalone(self) -> bool:
        """Return whether subnet template model is a standalone model.

        Standalone means that the template is not part of a larger template.

        Returns
        -------
            bool: True if standalone. False otherwise.

        """
        return self.vpc_id is None

from ipaddress import IPv4Network

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..core.db.database import Base
from ..core.db.ipv4_network_type import IPv4NetworkType
from .mixin_models import OwnableObjectMixin


class SubnetMixin(MappedAsDataclass):
    """Common Subnet attributes."""

    name: Mapped[str] = mapped_column(String, nullable=False)
    cidr: Mapped[IPv4Network] = mapped_column(IPv4NetworkType, nullable=False)


# ==================== Blueprints =====================


class BlueprintSubnetModel(Base, OwnableObjectMixin, SubnetMixin):
    """SQLAlchemy ORM model for blueprint subnet objects."""

    __tablename__ = "blueprint_subnets"

    # Parent relationship
    vpc_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("blueprint_vpcs.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )
    vpc = relationship("BlueprintVPCModel", back_populates="subnets")

    # Child relationship
    hosts = relationship(
        "BlueprintHostModel",
        back_populates="subnet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def is_standalone(self) -> bool:
        """Return whether blueprint subnet model is standalone.

        Standalone means that the blueprint is not part of a larger blueprint.

        Returns
        -------
            bool: True if standalone. False otherwise.

        """
        return self.vpc_id is None


# ==================== Deployed (Instances) =====================


class DeployedSubnetModel(Base, OwnableObjectMixin, SubnetMixin):
    """SQLAlchemy ORM model for deployed subnet objects."""

    __tablename__ = "deployed_subnets"

    resource_id: Mapped[str] = mapped_column(String, nullable=False)

    # Parent relationship
    vpc_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("deployed_vpcs.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )
    vpc = relationship("DeployedVPCModel", back_populates="subnets")

    # Child relationship
    hosts = relationship(
        "DeployedHostModel",
        back_populates="subnet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

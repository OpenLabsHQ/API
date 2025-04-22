from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from ..core.db.database import Base
from ..enums.permissions import PermissionEntityType, PermissionType


class BlueprintPermissionModel(Base, MappedAsDataclass):
    """SQLAlchemy ORM model for blueprint permissions."""

    __tablename__ = "blueprint_permissions"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        init=False,  # Allow DB to generate ID
    )

    # The blueprint this permission applies to
    # We need polymorphic references as permissions can apply to any blueprint type
    blueprint_type: Mapped[str] = mapped_column(String, nullable=False)
    blueprint_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # The entity this permission is granted to
    entity_type: Mapped[PermissionEntityType] = mapped_column(
        Enum(PermissionEntityType),
        nullable=False,
    )
    entity_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # The type of permission
    permission_type: Mapped[PermissionType] = mapped_column(
        Enum(PermissionType),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        init=False,
    )
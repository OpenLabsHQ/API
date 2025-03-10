from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from ..enums.providers import OpenLabsProvider
from .template_base_model import OwnableObjectMixin


class TemplateRangeModel(Base, OwnableObjectMixin):
    """SQLAlchemy ORM model for template range objects."""

    __tablename__ = "range_templates"

    name: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[OpenLabsProvider] = mapped_column(
        Enum(OpenLabsProvider), nullable=False
    )
    vnc: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    vpn: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # One-to-many relationship with VPCs
    vpcs = relationship(
        "TemplateVPCModel", back_populates="range", cascade="all, delete-orphan"
    )

    def is_standalone(self) -> bool:
        """Return whether host template model is a standalone model.

        Standalone means that the template is not part of a larger template.

        Returns
        -------
            bool: True if standalone. False otherwise.

        """
        # Ranges are currently the highest level template object
        return True

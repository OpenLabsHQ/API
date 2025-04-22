from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .mixin_models import OwnableObjectMixin


class WorkspaceModel(Base, OwnableObjectMixin):
    """Model for workspaces."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    default_time_limit: Mapped[int] = mapped_column(
        Integer, default=3600, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, init=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        init=False,
    )

    # Relationships
    workspace_users = relationship(
        "WorkspaceUserModel", back_populates="workspace", cascade="all, delete-orphan"
    )
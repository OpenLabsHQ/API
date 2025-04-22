from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from ..core.db.database import Base
from ..enums.workspace_roles import WorkspaceRole

class WorkspaceUserModel(Base, MappedAsDataclass):
    """Model for workspace-user associations."""

    __tablename__ = "workspace_users"

    workspace_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # Need to come up with a good convention for unlimited time limit.
    # Could just be max int or something like that
    time_limit: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole), default=WorkspaceRole.MEMBER, nullable=False
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
    workspace = relationship("WorkspaceModel", back_populates="workspace_users")
    user = relationship("UserModel", back_populates="workspace_users")
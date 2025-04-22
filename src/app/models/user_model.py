from datetime import datetime

from sqlalchemy import Boolean, DateTime, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base
from .mixin_models import OpenLabsUserMixin


class UserModel(Base, OpenLabsUserMixin):
    """SQLAlchemy ORM model for User."""

    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Encryption-related fields
    public_key: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    encrypted_private_key: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )
    key_salt: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True, default=None
    )

    # One-to-one relationship with secrets.
    # For now, users can only have one azure or one aws secret
    secrets = relationship(
        "SecretModel",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    # Relationship with workspaces through workspace_users
    workspace_users = relationship(
        "WorkspaceUserModel", back_populates="user", cascade="all, delete-orphan"
    )

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class SecretModel(Base):
    """SQLAlchemy ORM model for OpenLabs Secrets.

    All secret fields are now stored encrypted using the user's public key.
    """

    __tablename__ = "secrets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, primary_key=True
    )

    # AWS credentials - encrypted with user's public key
    aws_access_key: Mapped[str] = mapped_column(Text, nullable=True)
    aws_secret_key: Mapped[str] = mapped_column(Text, nullable=True)
    aws_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Azure credentials - encrypted with user's public key
    azure_client_id: Mapped[str] = mapped_column(Text, nullable=True)
    azure_client_secret: Mapped[str] = mapped_column(Text, nullable=True)
    azure_tenant_id: Mapped[str] = mapped_column(Text, nullable=True)
    azure_subscription_id: Mapped[str] = mapped_column(Text, nullable=True)
    azure_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("UserModel", back_populates="secrets")

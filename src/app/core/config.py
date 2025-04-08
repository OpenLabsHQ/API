import os

from pydantic_settings import BaseSettings
from setuptools_scm import get_version
from starlette.config import Config

from ..utils.cdktf_utils import create_cdktf_dir

current_file_dir = os.path.dirname(os.path.realpath(__file__))
env_path = os.path.join(current_file_dir, "..", "..", "..", ".env")
config = Config(env_path)


class AppSettings(BaseSettings):
    """FastAPI app settings."""

    APP_NAME: str = config("APP_NAME", default="OpenLabs API")
    APP_DESCRIPTION: str | None = config(
        "APP_DESCRIPTION", default="OpenLabs backend API."
    )
    APP_VERSION: str | None = config(
        "APP_VERSION", default=get_version()
    )  # Latest tagged release
    LICENSE_NAME: str | None = config("LICENSE", default="GPLv3")
    LICENSE_URL: str | None = config(
        "LICENSE_URL",
        default="https://github.com/OpenLabsHQ/API?tab=GPL-3.0-1-ov-file#readme",
    )
    CONTACT_NAME: str | None = config("CONTACT_NAME", default="OpenLabs Support")
    CONTACT_EMAIL: str | None = config("CONTACT_EMAIL", default="support@openlabs.sh")


class AuthSettings(BaseSettings):
    """Authentication settings."""

    SECRET_KEY: str = config("SECRET_KEY", default="ChangeMe123!")
    ALGORITHM: str = config("ALGORITHM", default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = config(
        "ACCESS_TOKEN_EXPIRE_MINUTES", default=60 * 24 * 7
    )  # One week

    # Admin user settings
    ADMIN_EMAIL: str = config("ADMIN_EMAIL", default="admin@test.com")
    ADMIN_PASSWORD: str = config("ADMIN_PASSWORD", default="admin123")
    ADMIN_NAME: str = config("ADMIN_NAME", default="Administrator")


class CDKTFSettings(BaseSettings):
    """CDKTF settings."""

    CDKTF_DIR: str = config("CDKTF_DIR", default=create_cdktf_dir())


class DatabaseSettings(BaseSettings):
    """Base class for database settings."""

    pass


class PostgresSettings(DatabaseSettings):
    """Postgres database settings."""

    POSTGRES_USER: str = config("POSTGRES_USER", default="postgres")
    POSTGRES_PASSWORD: str = config("POSTGRES_PASSWORD", default="postgres")
    POSTGRES_SERVER: str = config("POSTGRES_SERVER", default="localhost")
    POSTGRES_PORT: int = config("POSTGRES_PORT", default=5432)
    POSTGRES_DB: str = config("POSTGRES_DB", default="postgres")
    POSTGRES_SYNC_PREFIX: str = config("POSTGRES_SYNC_PREFIX", default="postgresql://")
    POSTGRES_ASYNC_PREFIX: str = config(
        "POSTGRES_ASYNC_PREFIX", default="postgresql+asyncpg://"
    )
    POSTGRES_URI: str = (
        f"{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    POSTGRES_URL: str | None = config("POSTGRES_URL", default=None)


class RedisQueueSettings(BaseSettings):
    """Redis queue settings."""

    REDIS_QUEUE_HOST: str = config("REDIS_QUEUE_HOST", default="localhost")
    REDIS_QUEUE_PORT: int = config("REDIS_QUEUE_PORT", default=6379)
    REDIS_QUEUE_PASSWORD: str = config("REDIS_QUEUE_PASSWORD", default="ChangeMe123!")


class Settings(
    AppSettings, PostgresSettings, CDKTFSettings, AuthSettings, RedisQueueSettings
):
    """FastAPI app settings."""

    pass


settings = Settings()

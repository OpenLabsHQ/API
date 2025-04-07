from typing import Any, Callable, ClassVar

from arq.connections import RedisSettings

from ...core.config import settings

# Import logger to ensure workers log messages properly
from ..logger import LOG_DIR  # noqa: F401
from .functions import deploy_range, shutdown, startup

REDIS_QUEUE_HOST = settings.REDIS_QUEUE_HOST
REDIS_QUEUE_PORT = settings.REDIS_QUEUE_PORT


class WorkerSettings:
    """Remote worker settings."""

    functions: ClassVar[list[Callable[..., Any]]] = [deploy_range]
    redis_settings = RedisSettings(host=REDIS_QUEUE_HOST, port=REDIS_QUEUE_PORT)
    on_startup = startup
    on_shutdown = shutdown
    handle_signals = False

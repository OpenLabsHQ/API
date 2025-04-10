import asyncio
import logging

import uvloop
from arq.worker import Worker

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)


async def startup(ctx: Worker) -> None:
    """Start worker."""
    logger.info("Worker started...")


async def shutdown(ctx: Worker) -> None:
    """Shutdown worker."""
    logger.info("Worker end...")

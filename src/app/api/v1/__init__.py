"""Version 1 of the OpenLabs API routes."""

from fastapi import APIRouter

from .auth import router as auth_router
from .health import router as health_router
from .ranges import router as ranges_router
from .templates import router as templates_router
from .users import router as user_router
from .jobs import router as job_router

router = APIRouter(prefix="/v1")
router.include_router(health_router)
router.include_router(templates_router)
router.include_router(ranges_router)
router.include_router(auth_router)
router.include_router(user_router)
router.include_router(job_router)

import logging

import arq.jobs as arq_job
from fastapi import APIRouter, HTTPException, status
from redis.asyncio import Redis

from ...core.utils import queue
from ...schemas.job import JobInfo

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


@router.get("/{job_id}")
async def get_job_info(job_id: str) -> JobInfo:
    """Return both status and job meta information for the requested job, including the result if available."""
    if not isinstance(queue.pool, Redis):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect to task queue!",
        )

    job = arq_job.Job(job_id, queue.pool)

    # Return result if available, otherwise job info
    redis_job_result = await job.result_info()
    if redis_job_result:
        job_data = dict(vars(redis_job_result))
    else:
        redis_job_info = await job.info()

        if not redis_job_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find job with ID: {job_id}",
            )

        job_status = await job.status()

        job_data = dict(vars(redis_job_info))
        job_data["status"] = job_status

    return JobInfo.model_validate(job_data, from_attributes=True)

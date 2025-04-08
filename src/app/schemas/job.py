from datetime import datetime
from typing import Any

from arq.jobs import JobStatus
from pydantic import BaseModel, Field


class Job(BaseModel):
    """Remote task executed as an ARQ job."""

    job_id: str = Field(..., description="ID of the job.")


class JobInfo(BaseModel):
    """Remote task information."""

    function: str = Field(..., description="Name of the function executed.")
    job_try: int | None = Field(
        default=None, ge=0, description="Number of times task has been attempted."
    )
    enqueue_time: datetime = Field(..., description="When the task was enqueued.")
    start_time: datetime | None = Field(
        default=None, description="Start time of the task."
    )
    finish_time: datetime | None = Field(
        default=None, description="Finish time of the task."
    )
    status: JobStatus = Field(
        ...,
        description="Current status of the task.",
        examples=[JobStatus.in_progress, JobStatus.complete],
    )
    result: Any | None = Field(
        default=None, description="Return value of the task, if available."
    )
    success: bool | None = Field(default=None, description="Whether job succeeded.")

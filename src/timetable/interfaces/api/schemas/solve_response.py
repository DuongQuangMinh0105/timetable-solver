
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from timetable.domain.entities.job import JobStatus


class SolveAcceptedResponse(BaseModel):
    job_id: UUID
    status: Literal[JobStatus.QUEUED] = JobStatus.QUEUED
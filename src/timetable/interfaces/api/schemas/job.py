from uuid import UUID

from pydantic import BaseModel, ConfigDict

from timetable.domain.entities.job import JobStatus


class JobCreateRequest(BaseModel):
    input_ref: str


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: JobStatus
    input_ref: str
    result_ref: str | None = None

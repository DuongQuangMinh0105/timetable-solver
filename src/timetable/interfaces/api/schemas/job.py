from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from timetable.domain.entities.job import JobStatus


class JobCreateRequest(BaseModel):
    input_ref: str = Field(min_length=1)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: JobStatus
    input_ref: str
    result_ref: str | None = None

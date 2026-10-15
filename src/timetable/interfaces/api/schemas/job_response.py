from uuid import UUID

from pydantic import BaseModel


class JobResponse(BaseModel):
    job_id: UUID
    status: str
    result_ref: str | None

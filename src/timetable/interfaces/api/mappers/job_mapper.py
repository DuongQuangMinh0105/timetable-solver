from uuid import UUID

from timetable.domain.entities.job import Job, JobStatus
from timetable.interfaces.api.schemas.job import (
    JobCreateRequest,
    JobResponse,
)


def create_request_to_entity(
    dto: JobCreateRequest,
    job_id: UUID,
) -> Job:
    """Convert a create request DTO into a Job entity."""
    return Job(
        id=job_id,
        status=JobStatus.QUEUED,
        input_ref=dto.input_ref,
        result_ref=None,
    )


def entity_to_response(job: Job) -> JobResponse:
    """Convert a Job entity into a response DTO."""
    return JobResponse(
        id=job.id,
        status=job.status,
        input_ref=job.input_ref,
        result_ref=job.result_ref,
    )

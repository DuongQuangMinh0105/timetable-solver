from uuid import uuid4

import pytest
from pydantic import ValidationError

from timetable.domain.entities.job import Job, JobStatus
from timetable.interfaces.api.mappers.job_mapper import (
    create_request_to_entity,
    entity_to_response,
)
from timetable.interfaces.api.schemas.job import (
    JobCreateRequest,
    JobResponse,
)


def test_create_request_to_entity() -> None:
    job_id = uuid4()
    dto = JobCreateRequest(input_ref="input/jobs/123.json")

    job = create_request_to_entity(dto, job_id)

    assert isinstance(job, Job)
    assert job.id == job_id
    assert job.status == JobStatus.QUEUED
    assert job.input_ref == "input/jobs/123.json"
    assert job.result_ref is None


def test_entity_to_response() -> None:
    job_id = uuid4()
    job = Job(
        id=job_id,
        status=JobStatus.COMPLETED,
        input_ref="input/jobs/123.json",
        result_ref="results/jobs/123.json",
    )

    response = entity_to_response(job)

    assert isinstance(response, JobResponse)
    assert response.id == job_id
    assert response.status == JobStatus.COMPLETED
    assert response.input_ref == "input/jobs/123.json"
    assert response.result_ref == "results/jobs/123.json"


def test_job_create_request_rejects_empty_input_ref() -> None:
    with pytest.raises(ValidationError):
        JobCreateRequest(input_ref="")


def test_job_response_accepts_missing_result_ref() -> None:
    response = JobResponse(
        id=uuid4(),
        status=JobStatus.QUEUED,
        input_ref="input/jobs/123.json",
    )

    assert response.result_ref is None

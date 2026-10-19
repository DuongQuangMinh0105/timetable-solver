from uuid import UUID, uuid4

import pytest

from timetable.application.use_cases.get_job import GetJob, JobNotFoundError
from timetable.domain.entities.job import Job, JobStatus


class _Repository:
    def __init__(self, *jobs: Job) -> None:
        self._jobs = {job.id: job for job in jobs}

    def save(self, job: Job) -> None:
        self._jobs[job.id] = job

    def get_by_id(self, job_id: UUID) -> Job | None:
        return self._jobs.get(job_id)

    def update(self, job: Job) -> None:
        self._jobs[job.id] = job


def test_get_job_returns_the_stored_job() -> None:
    job = Job(id=uuid4(), status=JobStatus.RUNNING, input_ref="in.json")

    assert GetJob(_Repository(job)).execute(job.id) is job


def test_get_job_raises_when_the_job_does_not_exist() -> None:
    missing = uuid4()

    with pytest.raises(JobNotFoundError, match=str(missing)):
        GetJob(_Repository()).execute(missing)

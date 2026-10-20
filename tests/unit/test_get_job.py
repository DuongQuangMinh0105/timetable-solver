from datetime import UTC, datetime
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

    def claim_queued_job(self, job_id: UUID) -> Job | None:
        job = self._jobs.get(job_id)

        if job is None or job.status is not JobStatus.QUEUED:
            return None

        job.status = JobStatus.RUNNING
        job.error_message = None
        return job

    def list_queued_jobs(
        self,
        limit: int = 100,
        after_id: UUID | None = None,
    ) -> list[Job]:
        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        queued_jobs = sorted(
            (
                job
                for job in self._jobs.values()
                if job.status is JobStatus.QUEUED and (after_id is None or job.id > after_id)
            ),
            key=lambda job: job.id,
        )
        return queued_jobs[:limit]

    def touch_heartbeat(self, job_id: UUID) -> bool:
        job = self._jobs.get(job_id)

        if job is None or job.status is not JobStatus.RUNNING:
            return False

        job.heartbeat_at = datetime.now(UTC)
        return True

    def list_stale_running_jobs(
        self,
        cutoff: datetime,
        limit: int = 100,
    ) -> list[Job]:
        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        stale_jobs = [
            job
            for job in self._jobs.values()
            if job.status is JobStatus.RUNNING
            and job.heartbeat_at is not None
            and job.heartbeat_at < cutoff
        ]

        return sorted(
            stale_jobs,
            key=lambda job: (job.heartbeat_at, job.id),
        )[:limit]

    def fail_stale_running_job(
        self,
        job_id: UUID,
        cutoff: datetime,
        error_message: str,
    ) -> bool:
        job = self._jobs.get(job_id)

        if (
            job is None
            or job.status is not JobStatus.RUNNING
            or job.heartbeat_at is None
            or job.heartbeat_at >= cutoff
        ):
            return False

        job.status = JobStatus.FAILED
        job.error_message = error_message
        return True


def test_get_job_returns_the_stored_job() -> None:
    job = Job(id=uuid4(), status=JobStatus.RUNNING, input_ref="in.json")

    assert GetJob(_Repository(job)).execute(job.id) is job


def test_get_job_raises_when_the_job_does_not_exist() -> None:
    missing = uuid4()

    with pytest.raises(JobNotFoundError, match=str(missing)):
        GetJob(_Repository()).execute(missing)

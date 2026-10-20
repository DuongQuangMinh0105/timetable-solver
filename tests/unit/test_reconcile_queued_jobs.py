from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from timetable.application.use_cases.reconcile_queued_jobs import (
    ReconcileQueuedJobs,
)
from timetable.domain.entities.job import Job, JobStatus


class FakeRepository:
    def __init__(self, jobs: list[Job]) -> None:
        self.jobs = sorted(jobs, key=lambda job: job.id)
        self.requested_limit: int | None = None
        self.requested_cursor: UUID | None = None

    def save(self, job: Job) -> None:
        self.jobs.append(job)
        self.jobs.sort(key=lambda item: item.id)

    def get_by_id(self, job_id: UUID) -> Job | None:
        return next((job for job in self.jobs if job.id == job_id), None)

    def update(self, job: Job) -> None:
        for index, existing_job in enumerate(self.jobs):
            if existing_job.id == job.id:
                self.jobs[index] = job
                return

        raise LookupError(f"Job {job.id} does not exist.")

    def claim_queued_job(self, job_id: UUID) -> Job | None:
        job = self.get_by_id(job_id)

        if job is None or job.status is not JobStatus.QUEUED:
            return None

        job.status = JobStatus.RUNNING
        job.error_message = None
        self.update(job)
        return job

    def list_queued_jobs(
        self,
        limit: int = 100,
        after_id: UUID | None = None,
    ) -> list[Job]:
        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        self.requested_limit = limit
        self.requested_cursor = after_id

        queued_jobs = [
            job
            for job in self.jobs
            if job.status is JobStatus.QUEUED and (after_id is None or job.id > after_id)
        ]
        return queued_jobs[:limit]

    def touch_heartbeat(self, job_id: UUID) -> bool:
        job = self.get_by_id(job_id)

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
            for job in self.jobs
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
        job = self.get_by_id(job_id)

        if (
            job is None
            or job.status is not JobStatus.RUNNING
            or job.heartbeat_at is None
            or job.heartbeat_at >= cutoff
        ):
            return False

        job.status = JobStatus.FAILED
        job.error_message = error_message
        self.update(job)
        return True


class FakeDispatcher:
    def __init__(self, failing_ids: set[str] | None = None) -> None:
        self.dispatched_ids: list[str] = []
        self.failing_ids = failing_ids or set()

    def dispatch(self, job_id: str) -> None:
        if job_id in self.failing_ids:
            raise RuntimeError("Redis unavailable")

        self.dispatched_ids.append(job_id)


def make_job(
    status: JobStatus = JobStatus.QUEUED,
    job_id: UUID | None = None,
) -> Job:
    return Job(
        id=job_id or uuid4(),
        status=status,
        input_ref="inputs/test.json",
    )


def test_reconcile_dispatches_queued_jobs() -> None:
    jobs = [make_job(), make_job()]
    repository = FakeRepository(jobs)
    dispatcher = FakeDispatcher()

    result = ReconcileQueuedJobs(repository, dispatcher).execute()

    assert result.scanned == 2
    assert result.dispatched == 2
    assert result.failed == 0
    assert set(dispatcher.dispatched_ids) == {str(job.id) for job in jobs}


def test_reconcile_continues_when_one_dispatch_fails() -> None:
    jobs = sorted([make_job(), make_job()], key=lambda job: job.id)
    repository = FakeRepository(jobs)
    dispatcher = FakeDispatcher(failing_ids={str(jobs[0].id)})

    result = ReconcileQueuedJobs(repository, dispatcher).execute()

    assert result.scanned == 2
    assert result.dispatched == 1
    assert result.failed == 1
    assert dispatcher.dispatched_ids == [str(jobs[1].id)]


def test_reconcile_respects_batch_size() -> None:
    jobs = [make_job() for _ in range(3)]
    repository = FakeRepository(jobs)
    dispatcher = FakeDispatcher()

    result = ReconcileQueuedJobs(
        repository,
        dispatcher,
        batch_size=2,
    ).execute()

    assert repository.requested_limit == 2
    assert result.scanned == 2
    assert result.dispatched == 2


def test_reconcile_moves_to_next_page() -> None:
    jobs = [make_job() for _ in range(5)]
    repository = FakeRepository(jobs)
    dispatcher = FakeDispatcher()
    reconciler = ReconcileQueuedJobs(
        repository,
        dispatcher,
        batch_size=2,
    )

    first = reconciler.execute()
    second = reconciler.execute()
    third = reconciler.execute()

    expected_ids = {str(job.id) for job in jobs}

    assert first.scanned == 2
    assert second.scanned == 2
    assert third.scanned == 1
    assert len(dispatcher.dispatched_ids) == 5
    assert set(dispatcher.dispatched_ids) == expected_ids


def test_reconcile_restarts_from_beginning_after_last_page() -> None:
    jobs = [make_job() for _ in range(3)]
    repository = FakeRepository(jobs)
    dispatcher = FakeDispatcher()
    reconciler = ReconcileQueuedJobs(
        repository,
        dispatcher,
        batch_size=2,
    )

    reconciler.execute()
    reconciler.execute()
    result = reconciler.execute()

    assert result.scanned == 2
    assert result.dispatched == 2


def test_reconcile_rejects_invalid_batch_size() -> None:
    repository = FakeRepository([])
    dispatcher = FakeDispatcher()

    with pytest.raises(ValueError, match="greater than zero"):
        ReconcileQueuedJobs(repository, dispatcher, batch_size=0)

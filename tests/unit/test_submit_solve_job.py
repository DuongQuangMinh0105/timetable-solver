
from datetime import UTC, datetime
from uuid import UUID

import pytest

from timetable.application.use_cases.submit_solve_job import SubmitSolveJob
from timetable.domain.entities.job import Job, JobStatus


class FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> None:
        self.files[key] = data

    def get(self, key: str) -> bytes:
        return self.files[key]

    def exists(self, key: str) -> bool:
        return key in self.files

    def delete(self, key: str) -> None:
        self.files.pop(key, None)


class FakeRepository:
    def __init__(self) -> None:
        self.jobs: list[Job] = []

    def save(self, job: Job) -> None:
        self.jobs.append(job)

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

        queued_jobs = sorted(
            (
                job
                for job in self.jobs
                if job.status is JobStatus.QUEUED
                and (after_id is None or job.id > after_id)
            ),
            key=lambda job: job.id,
        )
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


class FailingRepository:
    def save(self, job: Job) -> None:
        raise RuntimeError("database unavailable")

    def get_by_id(self, job_id: UUID) -> Job | None:
        return None

    def update(self, job: Job) -> None:
        raise LookupError(f"Job {job.id} does not exist.")

    def claim_queued_job(self, job_id: UUID) -> Job | None:
        return None

    def list_queued_jobs(
        self,
        limit: int = 100,
        after_id: UUID | None = None,
    ) -> list[Job]:
        if limit < 1:
            raise ValueError("limit must be greater than zero.")
        return []

    def touch_heartbeat(self, job_id: UUID) -> bool:
        return False

    def list_stale_running_jobs(
        self,
        cutoff: datetime,
        limit: int = 100,
    ) -> list[Job]:
        if limit < 1:
            raise ValueError("limit must be greater than zero.")
        return []

    def fail_stale_running_job(
        self,
        job_id: UUID,
        cutoff: datetime,
        error_message: str,
    ) -> bool:
        return False


class RecordingDispatcher:
    def __init__(self) -> None:
        self.dispatched_ids: list[str] = []

    def dispatch(self, job_id: str) -> None:
        self.dispatched_ids.append(job_id)


class FailingDispatcher:
    def dispatch(self, job_id: str) -> None:
        raise RuntimeError("redis unavailable")


def test_submit_saves_input_creates_queued_job_and_dispatches() -> None:
    storage = FakeStorage()
    repository = FakeRepository()
    dispatcher = RecordingDispatcher()
    use_case = SubmitSolveJob(repository, storage, dispatcher)

    payload: dict[str, object] = {
        "schema_version": "0.1",
        "grid": {"days": 6},
    }

    result = use_case.execute(payload)

    assert len(repository.jobs) == 1
    job = repository.jobs[0]

    assert job.status is JobStatus.QUEUED
    assert isinstance(job.id, UUID)
    assert storage.exists(job.input_ref)
    assert storage.get(job.input_ref)
    assert dispatcher.dispatched_ids == [str(job.id)]
    assert result.job_id == job.id
    assert result.status is JobStatus.QUEUED


def test_submit_cleans_input_and_does_not_dispatch_if_save_fails() -> None:
    storage = FakeStorage()
    dispatcher = RecordingDispatcher()
    use_case = SubmitSolveJob(FailingRepository(), storage, dispatcher)

    payload: dict[str, object] = {"schema_version": "0.1"}

    with pytest.raises(RuntimeError, match="database unavailable"):
        use_case.execute(payload)

    assert storage.files == {}
    assert dispatcher.dispatched_ids == []


def test_submit_dispatch_failure_leaves_job_queued() -> None:
    repository = FakeRepository()
    storage = FakeStorage()
    dispatcher = FailingDispatcher()

    result = SubmitSolveJob(
        repository=repository,
        storage=storage,
        dispatcher=dispatcher,
    ).execute({"example": "payload"})

    assert len(repository.jobs) == 1
    saved_job = repository.get_by_id(result.job_id)

    assert saved_job is not None
    assert saved_job.status is JobStatus.QUEUED
    assert storage.exists(saved_job.input_ref)
    assert result.job_id == saved_job.id
    assert result.status is JobStatus.QUEUED

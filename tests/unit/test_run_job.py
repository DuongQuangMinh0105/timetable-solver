from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from timetable.application.use_cases.run_job import JobNotFoundError, RunJob
from timetable.domain.entities.job import Job, JobStatus
from timetable.infrastructure.solver.fake import fake_handler
from timetable.infrastructure.storage.local import LocalStorage


class InMemoryJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[UUID, Job] = {}

    def save(self, job: Job) -> None:
        self.jobs[job.id] = job

    def get_by_id(self, job_id: UUID) -> Job | None:
        return self.jobs.get(job_id)

    def update(self, job: Job) -> None:
        self.jobs[job.id] = job

    def claim_queued_job(self, job_id: UUID) -> Job | None:
        job = self.jobs.get(job_id)

        if job is None or job.status is not JobStatus.QUEUED:
            return None

        job.status = JobStatus.RUNNING
        job.error_message = None
        self.jobs[job_id] = job
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
                for job in self.jobs.values()
                if job.status is JobStatus.QUEUED and (after_id is None or job.id > after_id)
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
            for job in self.jobs.values()
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


def make_job(storage: LocalStorage, repo: InMemoryJobRepository) -> Job:
    job = Job(
        id=uuid4(),
        status=JobStatus.QUEUED,
        input_ref="jobs/in/input.json",
    )
    storage.put(job.input_ref, b"{}")
    repo.save(job)
    return job


def test_run_job_completes(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    repo = InMemoryJobRepository()
    job = make_job(storage, repo)

    done = RunJob(repo, storage, fake_handler).execute(job.id)

    assert done.status is JobStatus.COMPLETED
    assert done.result_ref is not None
    assert storage.exists(done.result_ref)


def test_run_job_marks_failed_and_reraises(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    repo = InMemoryJobRepository()
    job = make_job(storage, repo)

    def boom(_: bytes) -> bytes:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        RunJob(repo, storage, boom).execute(job.id)

    failed_job = repo.jobs[job.id]
    assert failed_job.status is JobStatus.FAILED
    assert failed_job.error_message == "boom"
    assert failed_job.result_ref is None


def test_run_job_not_found(tmp_path: Path) -> None:
    with pytest.raises(JobNotFoundError):
        RunJob(
            InMemoryJobRepository(),
            LocalStorage(tmp_path),
            fake_handler,
        ).execute(uuid4())


def test_run_completed_job_does_not_execute_handler_again(
    tmp_path: Path,
) -> None:
    storage = LocalStorage(tmp_path)
    repo = InMemoryJobRepository()
    job = make_job(storage, repo)
    calls = 0

    def handler(_: bytes) -> bytes:
        nonlocal calls
        calls += 1
        return b'{"ok": true}'

    use_case = RunJob(repo, storage, handler)

    first_result = use_case.execute(job.id)
    second_result = use_case.execute(job.id)

    assert first_result.status is JobStatus.COMPLETED
    assert second_result.status is JobStatus.COMPLETED
    assert calls == 1


def test_run_failed_job_does_not_execute_handler_again(
    tmp_path: Path,
) -> None:
    storage = LocalStorage(tmp_path)
    repo = InMemoryJobRepository()
    job = make_job(storage, repo)
    calls = 0

    def handler(_: bytes) -> bytes:
        nonlocal calls
        calls += 1
        raise RuntimeError("solver failed")

    use_case = RunJob(repo, storage, handler)

    with pytest.raises(RuntimeError, match="solver failed"):
        use_case.execute(job.id)

    result = use_case.execute(job.id)

    assert result.status is JobStatus.FAILED
    assert result.error_message == "solver failed"
    assert calls == 1

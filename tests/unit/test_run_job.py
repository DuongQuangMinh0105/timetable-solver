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


def make_job(storage: LocalStorage, repo: InMemoryJobRepository) -> Job:
    job = Job(id=uuid4(), status=JobStatus.QUEUED, input_ref="jobs/in/input.json")
    storage.put(job.input_ref, b"{}")
    repo.save(job)
    return job


def test_run_job_completes(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    repo = InMemoryJobRepository()
    job = make_job(storage, repo)

    done = RunJob(repo, storage, fake_handler).execute(job.id)

    assert done.status == JobStatus.COMPLETED
    assert done.result_ref is not None
    assert storage.exists(done.result_ref)


def test_run_job_marks_failed_and_reraises(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    repo = InMemoryJobRepository()
    job = make_job(storage, repo)

    def boom(_: bytes) -> bytes:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        RunJob(repo, storage, boom).execute(job.id)

    assert repo.jobs[job.id].status == JobStatus.FAILED
    assert repo.jobs[job.id].result_ref is None


def test_run_job_not_found(tmp_path: Path) -> None:
    with pytest.raises(JobNotFoundError):
        RunJob(InMemoryJobRepository(), LocalStorage(tmp_path), fake_handler).execute(uuid4())

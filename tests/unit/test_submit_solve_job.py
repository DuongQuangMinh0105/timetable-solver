
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


class FailingRepository:
    def save(self, job: Job) -> None:
        raise RuntimeError("database unavailable")

    def get_by_id(self, job_id: UUID) -> Job | None:
        return None

    def update(self, job: Job) -> None:
        raise LookupError(f"Job {job.id} does not exist.")


class RecordingDispatcher:
    def __init__(self) -> None:
        self.dispatched_ids: list[str] = []

    def dispatch(self, job_id: str) -> None:
        self.dispatched_ids.append(job_id)


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
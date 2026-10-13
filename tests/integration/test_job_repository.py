from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete

from timetable.domain.entities.job import Job, JobStatus
from timetable.infrastructure.persistence.database import SessionFactory
from timetable.infrastructure.persistence.job_repository import JobRepository
from timetable.infrastructure.persistence.models import JobModel


@pytest.fixture
def cleanup_job() -> Iterator[UUID]:
    job_id = uuid4()
    yield job_id

    with SessionFactory() as session:
        session.execute(delete(JobModel).where(JobModel.id == job_id))
        session.commit()


def test_save_and_get_by_id(cleanup_job: UUID) -> None:
    job = Job(
        id=cleanup_job,
        status=JobStatus.QUEUED,
        input_ref="test-input.json",
    )
    repository = JobRepository()

    repository.save(job)
    actual = repository.get_by_id(job.id)

    assert actual == job


def test_get_by_id_returns_none_for_missing_job() -> None:
    repository = JobRepository()

    assert repository.get_by_id(uuid4()) is None


def test_update_existing_job(cleanup_job: UUID) -> None:
    repository = JobRepository()
    original = Job(
        id=cleanup_job,
        status=JobStatus.QUEUED,
        input_ref="test-input.json",
    )
    repository.save(original)

    updated = Job(
        id=cleanup_job,
        status=JobStatus.COMPLETED,
        input_ref="test-input.json",
        result_ref="test-result.json",
    )
    repository.update(updated)

    assert repository.get_by_id(cleanup_job) == updated


def test_update_missing_job_raises_lookup_error() -> None:
    repository = JobRepository()
    missing_job = Job(
        id=uuid4(),
        status=JobStatus.RUNNING,
        input_ref="test-input.json",
    )

    with pytest.raises(LookupError, match="does not exist"):
        repository.update(missing_job)

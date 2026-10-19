from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
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
        status=JobStatus.FAILED,
        input_ref="test-input.json",
        error_message="Solver failed",
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


def test_claim_queued_job_changes_status_to_running(
    cleanup_job: UUID,
) -> None:
    repository = JobRepository()
    job = Job(
        id=cleanup_job,
        status=JobStatus.QUEUED,
        input_ref="test-input.json",
    )
    repository.save(job)

    claimed = repository.claim_queued_job(cleanup_job)

    assert claimed is not None
    assert claimed.id == cleanup_job
    assert claimed.status is JobStatus.RUNNING
    assert claimed.error_message is None

    persisted = repository.get_by_id(cleanup_job)
    assert persisted is not None
    assert persisted.status is JobStatus.RUNNING


def test_claim_queued_job_returns_none_after_first_claim(
    cleanup_job: UUID,
) -> None:
    repository = JobRepository()
    repository.save(
        Job(
            id=cleanup_job,
            status=JobStatus.QUEUED,
            input_ref="test-input.json",
        )
    )

    first_claim = repository.claim_queued_job(cleanup_job)
    second_claim = repository.claim_queued_job(cleanup_job)

    assert first_claim is not None
    assert first_claim.status is JobStatus.RUNNING
    assert second_claim is None


def test_concurrent_claim_only_allows_one_worker(
    cleanup_job: UUID,
) -> None:
    repository = JobRepository()
    repository.save(
        Job(
            id=cleanup_job,
            status=JobStatus.QUEUED,
            input_ref="test-input.json",
        )
    )

    barrier = Barrier(2)

    def claim_job() -> Job | None:
        # Start both database claims at approximately the same time.
        barrier.wait(timeout=5)
        return repository.claim_queued_job(cleanup_job)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(claim_job),
            executor.submit(claim_job),
        ]
        results = [future.result(timeout=10) for future in futures]

    successful_claims = [job for job in results if job is not None]
    rejected_claims = [job for job in results if job is None]

    assert len(successful_claims) == 1
    assert len(rejected_claims) == 1
    assert successful_claims[0].id == cleanup_job
    assert successful_claims[0].status is JobStatus.RUNNING

    persisted = repository.get_by_id(cleanup_job)
    assert persisted is not None
    assert persisted.status is JobStatus.RUNNING


def test_claim_non_queued_job_returns_none(
    cleanup_job: UUID,
) -> None:
    repository = JobRepository()
    completed_job = Job(
        id=cleanup_job,
        status=JobStatus.COMPLETED,
        input_ref="test-input.json",
        result_ref="jobs/result.json",
    )
    repository.save(completed_job)

    claimed = repository.claim_queued_job(cleanup_job)

    assert claimed is None
    assert repository.get_by_id(cleanup_job) == completed_job


def test_list_queued_jobs_returns_only_queued_jobs() -> None:
    repository = JobRepository()
    queued_id = uuid4()
    completed_id = uuid4()

    try:
        repository.save(
            Job(
                id=queued_id,
                status=JobStatus.QUEUED,
                input_ref="queued-input.json",
            )
        )
        repository.save(
            Job(
                id=completed_id,
                status=JobStatus.COMPLETED,
                input_ref="completed-input.json",
                result_ref="completed-result.json",
            )
        )

        jobs = repository.list_queued_jobs(limit=100)
        job_ids = {job.id for job in jobs}

        assert queued_id in job_ids
        assert completed_id not in job_ids
    finally:
        with SessionFactory() as session:
            session.execute(delete(JobModel).where(JobModel.id.in_([queued_id, completed_id])))
            session.commit()


def test_list_queued_jobs_rejects_non_positive_limit() -> None:
    repository = JobRepository()

    with pytest.raises(ValueError, match="greater than zero"):
        repository.list_queued_jobs(limit=0)


def test_list_queued_jobs_supports_pagination() -> None:
    repository = JobRepository()
    job_ids = {uuid4(), uuid4(), uuid4()}

    try:
        for job_id in job_ids:
            repository.save(
                Job(
                    id=job_id,
                    status=JobStatus.QUEUED,
                    input_ref=f"inputs/{job_id}.json",
                )
            )

        found_ids: set[UUID] = set()
        cursor: UUID | None = None

        # Other tests may leave queued jobs in the shared database.
        while not job_ids.issubset(found_ids):
            page = repository.list_queued_jobs(
                limit=2,
                after_id=cursor,
            )

            if not page:
                break

            page_ids = [job.id for job in page]

            if cursor is not None:
                assert all(job_id > cursor for job_id in page_ids)

            found_ids.update(page_ids)
            next_cursor = page[-1].id

            assert cursor is None or next_cursor > cursor
            cursor = next_cursor

        assert job_ids.issubset(found_ids)
    finally:
        with SessionFactory() as session:
            session.execute(delete(JobModel).where(JobModel.id.in_(job_ids)))
            session.commit()

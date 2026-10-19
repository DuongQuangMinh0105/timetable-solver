from collections.abc import Callable
from uuid import UUID

from timetable.application.ports.storage import StoragePort
from timetable.domain.entities.job import Job, JobStatus
from timetable.domain.ports.job_repository import JobRepositoryPort

JobHandler = Callable[[bytes], bytes]


class JobNotFoundError(Exception):
    """Không tìm thấy job theo id."""


class RunJob:
    """Run a queued job and persist its result and final status."""

    def __init__(
        self,
        repository: JobRepositoryPort,
        storage: StoragePort,
        handler: JobHandler,
        timeout_seconds: int = 300,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._handler = handler
        self._timeout_seconds = timeout_seconds

    def execute(self, job_id: UUID) -> Job:
        job = self._repository.get_by_id(job_id)

        if job is None:
            raise JobNotFoundError(str(job_id))

        claimed_job = self._repository.claim_queued_job(job_id)

        if claimed_job is None:
            # Another worker may already have claimed or completed the job.
            current_job = self._repository.get_by_id(job_id)

            if current_job is None:
                raise JobNotFoundError(str(job_id))

            return current_job

        job = claimed_job

        try:
            input_data = self._storage.get(job.input_ref)
            output = self._handler(input_data)

            result_ref = f"jobs/{job.id}/result.json"
            self._storage.put(result_ref, output)

        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error_message = str(exc) or type(exc).__name__
            self._repository.update(job)
            raise

        job.result_ref = result_ref
        job.status = JobStatus.COMPLETED
        job.error_message = None
        self._repository.update(job)

        return job

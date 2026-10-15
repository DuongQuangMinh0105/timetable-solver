from uuid import UUID

from timetable.domain.entities.job import Job
from timetable.domain.ports.job_repository import JobRepositoryPort


class JobNotFoundError(Exception):
    """Raised when a job cannot be found."""


class GetJob:
    """Retrieve a job by its ID."""

    def __init__(self, repository: JobRepositoryPort) -> None:
        self._repository = repository

    def execute(self, job_id: UUID) -> Job:
        job = self._repository.get_by_id(job_id)
        if job is None:
            raise JobNotFoundError(str(job_id))
        return job

from typing import Protocol
from uuid import UUID

from timetable.domain.entities.job import Job


class JobRepositoryPort(Protocol):
    def save(self, job: Job) -> None:
        """Persist a job."""

    def get_by_id(self, job_id: UUID) -> Job | None:
        """Retrieve a job by its ID."""

    def update(self, job: Job) -> None:
        """Update an existing job."""

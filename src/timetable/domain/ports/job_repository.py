from typing import Protocol
from uuid import UUID

from timetable.domain.entities.job import Job


class JobRepositoryPort(Protocol):
    """Contract for persisting and claiming jobs."""

    def save(self, job: Job) -> None:
        """Persist a job."""

    def get_by_id(self, job_id: UUID) -> Job | None:
        """Retrieve a job by its ID."""

    def update(self, job: Job) -> None:
        """Update an existing job."""

    def claim_queued_job(self, job_id: UUID) -> Job | None:
        """Atomically claim a queued job for processing."""

    def list_queued_jobs(
        self,
        limit: int = 100,
        after_id: UUID | None = None,
    ) -> list[Job]:
        """Return a bounded page of queued jobs after the given UUID."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from timetable.domain.entities.job import Job


class JobRepositoryPort(Protocol):
    """Contract for persisting, claiming and monitoring jobs."""

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
        """Return a bounded page of queued jobs."""

    def touch_heartbeat(self, job_id: UUID) -> bool:
        """Update heartbeat only while the job is running."""

    def list_stale_running_jobs(
        self,
        cutoff: datetime,
        limit: int = 100,
    ) -> list[Job]:
        """List running jobs whose heartbeat is older than cutoff."""

    def fail_stale_running_job(
        self,
        job_id: UUID,
        cutoff: datetime,
        error_message: str,
    ) -> bool:
        """Atomically fail a still-stale running job."""

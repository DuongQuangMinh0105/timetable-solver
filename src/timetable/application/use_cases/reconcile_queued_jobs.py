import logging
from dataclasses import dataclass
from uuid import UUID

from timetable.application.ports.job_dispatcher import JobDispatcherPort
from timetable.domain.entities.job import JobStatus
from timetable.domain.ports.job_repository import JobRepositoryPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ReconcileQueuedJobsResult:
    scanned: int
    dispatched: int
    failed: int


class ReconcileQueuedJobs:
    """Redispatch queued jobs that may be missing from the queue."""

    def __init__(
        self,
        repository: JobRepositoryPort,
        dispatcher: JobDispatcherPort,
        batch_size: int = 100,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero.")

        self._repository = repository
        self._dispatcher = dispatcher
        self._batch_size = batch_size
        self._cursor: UUID | None = None

    def execute(self) -> ReconcileQueuedJobsResult:
        jobs = self._repository.list_queued_jobs(
            limit=self._batch_size,
            after_id=self._cursor,
        )

        # Reached the end of the current ordered result set.
        # Reset so the next reconciliation cycle starts at the beginning.
        if not jobs and self._cursor is not None:
            self._cursor = None
            jobs = self._repository.list_queued_jobs(
                limit=self._batch_size,
            )

        dispatched = 0
        failed = 0

        for job in jobs:
            if job.status is not JobStatus.QUEUED:
                continue

            try:
                self._dispatcher.dispatch(str(job.id))
                dispatched += 1
            except Exception:
                failed += 1
                logger.exception(
                    "Could not redispatch queued job %s",
                    job.id,
                )

        if jobs:
            self._cursor = jobs[-1].id

        return ReconcileQueuedJobsResult(
            scanned=len(jobs),
            dispatched=dispatched,
            failed=failed,
        )

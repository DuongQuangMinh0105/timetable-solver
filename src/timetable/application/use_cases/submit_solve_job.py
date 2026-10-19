import json
import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from timetable.application.ports.job_dispatcher import JobDispatcherPort
from timetable.application.ports.storage import StoragePort
from timetable.domain.entities.job import Job, JobStatus
from timetable.domain.ports.job_repository import JobRepositoryPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SubmitSolveJobResult:
    job_id: UUID
    status: JobStatus


class SubmitSolveJob:
    def __init__(
        self,
        repository: JobRepositoryPort,
        storage: StoragePort,
        dispatcher: JobDispatcherPort,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._dispatcher = dispatcher

    def execute(self, payload: dict[str, object]) -> SubmitSolveJobResult:
        job_id = uuid4()
        input_ref = f"inputs/{job_id}.json"
        input_data = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        self._storage.put(input_ref, input_data)

        job = Job(
            id=job_id,
            status=JobStatus.QUEUED,
            input_ref=input_ref,
            result_ref=None,
        )

        try:
            self._repository.save(job)
        except Exception:
            # Remove the input file if the job could not be persisted.
            self._storage.delete(input_ref)
            raise

        try:
            self._dispatcher.dispatch(str(job_id))
        except Exception:
            # The dispatch result may be ambiguous: Redis might have received
            # the message before the connection failed. Keep the job queued
            # so reconciliation can retry without creating a replacement job.
            logger.exception(
                "Dispatch failed for job %s; keeping it queued for reconciliation",
                job_id,
            )

        return SubmitSolveJobResult(
            job_id=job_id,
            status=JobStatus.QUEUED,
        )

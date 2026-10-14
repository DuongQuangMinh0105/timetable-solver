import json
from dataclasses import dataclass
from uuid import UUID, uuid4

from timetable.application.ports.job_dispatcher import JobDispatcherPort
from timetable.application.ports.storage import StoragePort
from timetable.domain.entities.job import Job, JobStatus
from timetable.domain.ports.job_repository import JobRepositoryPort


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
            # Avoid leaving an orphaned input file if job persistence fails.
            self._storage.delete(input_ref)
            raise

        self._dispatcher.dispatch(str(job_id))

        return SubmitSolveJobResult(
            job_id=job_id,
            status=JobStatus.QUEUED,
        )

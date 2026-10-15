from collections.abc import Callable
from uuid import UUID

from timetable.application.ports.storage import StoragePort
from timetable.domain.entities.job import Job, JobStatus
from timetable.domain.ports.job_repository import JobRepositoryPort

JobHandler = Callable[[bytes], bytes]


class JobNotFoundError(Exception):
    """Không tìm thấy job theo id."""


class RunJob:
    """Chạy một job: đọc input từ storage, xử lý, ghi kết quả, cập nhật trạng thái.

    `handler` nhận bytes đầu vào và trả bytes kết quả. Hôm nay là solver giả,
    sau này sẽ thay bằng handler gọi SolveTimetable.
    """

    def __init__(
        self,
        repository: JobRepositoryPort,
        storage: StoragePort,
        handler: JobHandler,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._handler = handler

    def execute(self, job_id: UUID) -> Job:
        job = self._repository.get_by_id(job_id)
        if job is None:
            raise JobNotFoundError(str(job_id))

        job.status = JobStatus.RUNNING
        self._repository.update(job)

        try:
            output = self._handler(self._storage.get(job.input_ref))
            result_ref = f"jobs/{job.id}/result.json"
            self._storage.put(result_ref, output)
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error_message = str(exc) or type(exc).__name__
            self._repository.update(job)
            raise

        job.result_ref = result_ref
        job.status = JobStatus.COMPLETED
        self._repository.update(job)
        return job

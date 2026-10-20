import json
from typing import Any
from uuid import UUID

from timetable.application.ports.storage import StoragePort
from timetable.application.use_cases.get_job import JobNotFoundError
from timetable.domain.ports.job_repository import JobRepositoryPort


class ResultNotReadyError(Exception):
    """Job chưa có kết quả (đang chạy, thất bại hoặc chưa ghi result.json)."""


class GetJobResult:
    """Đọc result.json của một job qua `result_ref`."""

    def __init__(self, repository: JobRepositoryPort, storage: StoragePort) -> None:
        self._repository = repository
        self._storage = storage

    def execute(self, job_id: UUID) -> dict[str, Any]:
        job = self._repository.get_by_id(job_id)
        if job is None:
            raise JobNotFoundError(str(job_id))
        if job.result_ref is None:
            raise ResultNotReadyError(str(job_id))
        try:
            data = self._storage.get(job.result_ref)
        except (KeyError, FileNotFoundError) as exc:
            raise ResultNotReadyError(str(job_id)) from exc
        result: dict[str, Any] = json.loads(data.decode("utf-8"))
        return result

import json
from typing import Any
from uuid import uuid4

import pytest

from timetable.application.use_cases.get_job import JobNotFoundError
from timetable.application.use_cases.get_job_result import GetJobResult, ResultNotReadyError
from timetable.domain.entities.job import Job, JobStatus


class _Repo:
    def __init__(self, job: Job | None) -> None:
        self._job = job

    def get_by_id(self, job_id: Any) -> Job | None:
        return self._job


class _Storage:
    def __init__(self, files: dict[str, bytes]) -> None:
        self._files = files

    def get(self, key: str) -> bytes:
        return self._files[key]


def _job(result_ref: str | None) -> Job:
    return Job(id=uuid4(), status=JobStatus.COMPLETED, input_ref="in", result_ref=result_ref)


def test_returns_parsed_result() -> None:
    job = _job("jobs/1/result.json")
    storage = _Storage({"jobs/1/result.json": json.dumps({"status": "OPTIMAL"}).encode()})
    use_case = GetJobResult(_Repo(job), storage)  # type: ignore[arg-type]
    assert use_case.execute(job.id) == {"status": "OPTIMAL"}


def test_unknown_job_raises() -> None:
    use_case = GetJobResult(_Repo(None), _Storage({}))  # type: ignore[arg-type]
    with pytest.raises(JobNotFoundError):
        use_case.execute(uuid4())


def test_job_without_result_ref_is_not_ready() -> None:
    job = _job(None)
    use_case = GetJobResult(_Repo(job), _Storage({}))  # type: ignore[arg-type]
    with pytest.raises(ResultNotReadyError):
        use_case.execute(job.id)


def test_missing_file_is_not_ready() -> None:
    job = _job("jobs/1/result.json")
    use_case = GetJobResult(_Repo(job), _Storage({}))  # type: ignore[arg-type]
    with pytest.raises(ResultNotReadyError):
        use_case.execute(job.id)

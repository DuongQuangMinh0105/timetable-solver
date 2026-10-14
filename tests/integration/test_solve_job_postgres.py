import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete

from conftest import SAMPLE_PATH
from timetable.application.use_cases.run_job import RunJob
from timetable.domain.entities.job import Job, JobStatus
from timetable.domain.services.timetable_checker import check_timetable
from timetable.infrastructure.persistence.database import SessionFactory
from timetable.infrastructure.persistence.job_repository import JobRepository
from timetable.infrastructure.persistence.models import JobModel
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.solve_handler import make_solve_handler
from timetable.infrastructure.storage.local import LocalStorage


def _run(tmp_path: Path, payload: bytes) -> tuple[RunJob, JobRepository, LocalStorage, Job]:
    storage = LocalStorage(tmp_path)
    repository = JobRepository()
    job = Job(id=uuid4(), status=JobStatus.QUEUED, input_ref="jobs/in/input.json")
    storage.put(job.input_ref, payload)
    repository.save(job)
    handler = make_solve_handler(CpSatSolver(), check_timetable)
    return RunJob(repository, storage, handler), repository, storage, job


def _cleanup(job: Job) -> None:
    with SessionFactory() as session:
        session.execute(delete(JobModel).where(JobModel.id == job.id))
        session.commit()


def test_solve_job_end_to_end_with_postgres(tmp_path: Path) -> None:
    data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    data["solver"] = {"time_limit_s": 30, "num_workers": 1, "random_seed": 0}
    run_job, repository, storage, job = _run(tmp_path, json.dumps(data).encode("utf-8"))

    try:
        run_job.execute(job.id)

        saved = repository.get_by_id(job.id)
        assert saved is not None
        assert saved.status == JobStatus.COMPLETED
        assert saved.result_ref is not None
        result = json.loads(storage.get(saved.result_ref))
        assert result["ok"] is True
        assert len(result["assignments"]) == len(data["lesson_units"])
    finally:
        _cleanup(job)


def test_solve_job_with_invalid_input_is_marked_failed(tmp_path: Path) -> None:
    run_job, repository, _storage, job = _run(tmp_path, b"khong phai json")

    try:
        with pytest.raises(ValueError):
            run_job.execute(job.id)

        saved = repository.get_by_id(job.id)
        assert saved is not None
        assert saved.status == JobStatus.FAILED
        assert saved.result_ref is None
    finally:
        _cleanup(job)

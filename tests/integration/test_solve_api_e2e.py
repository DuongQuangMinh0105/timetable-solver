import json
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from conftest import SAMPLE_PATH
from timetable.application.use_cases.submit_solve_job import SubmitSolveJob
from timetable.container import create_submit_solve_job
from timetable.domain.entities.job import JobStatus
from timetable.infrastructure.dispatch.local import LocalJobDispatcher
from timetable.infrastructure.persistence.database import SessionFactory
from timetable.infrastructure.persistence.job_repository import JobRepository
from timetable.infrastructure.persistence.models import JobModel
from timetable.infrastructure.storage.local import LocalStorage
from timetable.infrastructure.storage.postgres import PostgresStorage
from timetable.interfaces.api.dependencies import get_submit_solve_job
from timetable.interfaces.api.main import app


def test_container_storage_follows_storage_dir_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """API và worker phải cùng đọc STORAGE_DIR, nếu không worker không thấy file input."""
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))

    use_case = create_submit_solve_job()
    use_case._storage.put("inputs/x.json", b"{}")

    assert (tmp_path / "inputs" / "x.json").read_bytes() == b"{}"


def test_post_solve_runs_worker_and_completes_job(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))  # tiến trình worker thừa hưởng biến này

    def build_use_case() -> SubmitSolveJob:
        # wait=True: chờ worker chạy xong để test kiểm tra được kết quả.
        return SubmitSolveJob(
            repository=JobRepository(),
            storage=LocalStorage(tmp_path),
            dispatcher=LocalJobDispatcher(wait=True),
        )

    payload = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    payload["solver"] = {"time_limit_s": 30, "num_workers": 1, "random_seed": 0}
    app.dependency_overrides[get_submit_solve_job] = build_use_case
    job_id: UUID | None = None

    try:
        response = TestClient(app).post("/solve", json=payload)
        assert response.status_code == 202
        job_id = UUID(response.json()["job_id"])

        job = JobRepository().get_by_id(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.result_ref is not None
        result = json.loads((tmp_path / job.result_ref).read_text(encoding="utf-8"))
        assert result["status"] in {"OPTIMAL", "FEASIBLE"}
        assert result["violations"] == []
        assert len(result["assignments"]) == len(payload["lesson_units"])
    finally:
        app.dependency_overrides.pop(get_submit_solve_job, None)
        if job_id is not None:
            with SessionFactory() as session:
                session.execute(delete(JobModel).where(JobModel.id == job_id))
                session.commit()


def test_post_solve_with_postgres_storage_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cấu hình như trên Render: không có ổ đĩa bền, file input và kết quả nằm trong Postgres."""
    monkeypatch.setenv("STORAGE_BACKEND", "postgres")  # tiến trình worker thừa hưởng biến này
    monkeypatch.setenv("SOLVER_MAX_WORKERS", "1")
    storage = PostgresStorage()

    def build_use_case() -> SubmitSolveJob:
        return SubmitSolveJob(
            repository=JobRepository(),
            storage=storage,
            dispatcher=LocalJobDispatcher(wait=True),
        )

    payload = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    payload["solver"] = {"time_limit_s": 30, "num_workers": 8, "random_seed": 0}
    app.dependency_overrides[get_submit_solve_job] = build_use_case
    job_id: UUID | None = None
    keys: list[str] = []

    try:
        response = TestClient(app).post("/solve", json=payload)
        assert response.status_code == 202
        job_id = UUID(response.json()["job_id"])

        job = JobRepository().get_by_id(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.result_ref is not None
        keys = [job.input_ref, job.result_ref]
        result = json.loads(storage.get(job.result_ref))
        assert result["status"] in {"OPTIMAL", "FEASIBLE"}
        assert len(result["assignments"]) == len(payload["lesson_units"])
    finally:
        app.dependency_overrides.pop(get_submit_solve_job, None)
        for key in keys:
            storage.delete(key)
        if job_id is not None:
            with SessionFactory() as session:
                session.execute(delete(JobModel).where(JobModel.id == job_id))
                session.commit()

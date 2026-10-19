import json
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from timetable.application.use_cases.submit_solve_job import SubmitSolveJob
from timetable.domain.entities.job import JobStatus
from timetable.infrastructure.dispatch.redis import RedisJobDispatcher
from timetable.infrastructure.persistence.database import SessionFactory
from timetable.infrastructure.persistence.job_repository import JobRepository
from timetable.infrastructure.persistence.models import JobModel
from timetable.infrastructure.storage.local import LocalStorage
from timetable.infrastructure.storage.postgres import PostgresStorage
from timetable.interfaces.api.dependencies import get_submit_solve_job
from timetable.interfaces.api.main import app

# Định nghĩa SAMPLE_PATH ở cấp độ module (đúng chuẩn và tránh lỗi type/used-before-def)
SAMPLE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "schema"
    / "input.sample.json"
)


def test_container_storage_follows_storage_dir_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The configured storage directory is used by the container."""
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))

    from timetable.container import create_submit_solve_job

    use_case = create_submit_solve_job()
    use_case._storage.put("inputs/x.json", b"{}")

    assert (tmp_path / "inputs" / "x.json").read_bytes() == b"{}"


def _run_redis_worker_e2e(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
    storage: LocalStorage | PostgresStorage,
    storage_backend: str,
    storage_dir: Path | None = None,
) -> None:
    """Submit a solve job through Redis and wait for a real worker to finish."""
    queue_name = f"timetable:test:{uuid4()}"
    api_key = "test-api-key"
    monkeypatch.setenv("STORAGE_BACKEND", storage_backend)
    monkeypatch.setenv("API_KEY", api_key)

    worker_env = os.environ.copy()
    worker_env["QUEUE_NAME"] = queue_name
    worker_env["STORAGE_BACKEND"] = storage_backend
    worker_env.setdefault("REDIS_URL", "redis://localhost:6379/0")

    if storage_dir is not None:
        monkeypatch.setenv("STORAGE_DIR", str(storage_dir))
        worker_env["STORAGE_DIR"] = str(storage_dir)

    def build_use_case() -> SubmitSolveJob:
        return SubmitSolveJob(
            repository=JobRepository(),
            storage=storage,
            dispatcher=RedisJobDispatcher(queue_name=queue_name),
        )

    app.dependency_overrides[get_submit_solve_job] = build_use_case
    worker: subprocess.Popen[bytes] | None = None
    job_id: UUID | None = None
    storage_keys: list[str] = []

    try:
        worker = subprocess.Popen(
            [sys.executable, "-m", "timetable.interfaces.worker.main"],
            env=worker_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        with TestClient(app) as client:
            response = client.post(
                "/solve",
                json=payload,
                headers={"X-API-Key": api_key},
            )

        assert response.status_code == 202, response.text

        response_body = response.json()
        assert isinstance(response_body, dict)
        response_job_id = response_body.get("job_id")
        assert isinstance(response_job_id, str)
        job_id = UUID(response_job_id)

        deadline = time.monotonic() + 60
        job = None

        while time.monotonic() < deadline:
            if worker.poll() is not None:
                pytest.fail(f"Redis worker exited unexpectedly: {worker.returncode}")

            job = JobRepository().get_by_id(job_id)

            if job is not None and job.status in {
                JobStatus.COMPLETED,
                JobStatus.FAILED,
            }:
                break

            time.sleep(0.25)

        assert job is not None, f"Job {job_id} was not found"
        assert job.status == JobStatus.COMPLETED, (
            f"Job ended with status {job.status}; error: {job.error_message}"
        )
        assert job.result_ref is not None

        storage_keys = [job.input_ref, job.result_ref]
        result_bytes = storage.get(job.result_ref)
        result: object = json.loads(result_bytes)

        assert isinstance(result, dict)

        status = result.get("status")
        violations = result.get("violations")
        assignments = result.get("assignments")
        lesson_units = payload.get("lesson_units")

        assert isinstance(status, str)
        assert status in {"OPTIMAL", "FEASIBLE"}
        assert isinstance(violations, list)
        assert violations == []
        assert isinstance(assignments, list)
        assert isinstance(lesson_units, list)
        assert len(assignments) == len(lesson_units)

    finally:
        app.dependency_overrides.pop(get_submit_solve_job, None)

        if worker is not None and worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=5)

        for key in storage_keys:
            storage.delete(key)

        if job_id is not None:
            with SessionFactory() as session:
                session.execute(delete(JobModel).where(JobModel.id == job_id))
                session.commit()


def test_post_solve_runs_redis_worker_and_completes_job(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The API dispatches a job through Redis to a separate worker."""
    payload = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)

    payload["solver"] = {
        "time_limit_s": 30,
        "num_workers": 1,
        "random_seed": 0,
    }

    _run_redis_worker_e2e(
        monkeypatch=monkeypatch,
        payload=payload,
        storage=LocalStorage(tmp_path),
        storage_backend="local",
        storage_dir=tmp_path,
    )


def test_post_solve_with_postgres_storage_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The API and worker share input/result files through Postgres storage."""
    monkeypatch.setenv("SOLVER_MAX_WORKERS", "1")

    payload = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)

    payload["solver"] = {
        "time_limit_s": 30,
        "num_workers": 1,
        "random_seed": 0,
    }

    _run_redis_worker_e2e(
        monkeypatch=monkeypatch,
        payload=payload,
        storage=PostgresStorage(),
        storage_backend="postgres",
    )
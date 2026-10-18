import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete

from conftest import SAMPLE_PATH
from timetable.domain.entities.job import Job, JobStatus
from timetable.infrastructure.persistence.database import SessionFactory
from timetable.infrastructure.persistence.job_repository import JobRepository
from timetable.infrastructure.persistence.models import JobModel
from timetable.infrastructure.storage.local import LocalStorage
from timetable.interfaces.worker.main import main as worker_main


def test_worker_with_job_id_runs_that_job_without_redis(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Chế độ của LocalJobDispatcher: có JOB_ID thì chạy đúng job đó rồi thoát, không đụng Redis."""
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")  # không ai nghe: chạm vào là lỗi
    data = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    data["solver"] = {"time_limit_s": 30, "num_workers": 1, "random_seed": 0}
    storage = LocalStorage(tmp_path)
    job = Job(id=uuid4(), status=JobStatus.QUEUED, input_ref=f"inputs/{uuid4()}.json")
    storage.put(job.input_ref, json.dumps(data).encode("utf-8"))
    JobRepository().save(job)
    monkeypatch.setenv("JOB_ID", str(job.id))

    try:
        worker_main()

        saved = JobRepository().get_by_id(job.id)
        assert saved is not None
        assert saved.status == JobStatus.COMPLETED
        assert saved.result_ref is not None
        assert storage.exists(saved.result_ref)
    finally:
        with SessionFactory() as session:
            session.execute(delete(JobModel).where(JobModel.id == job.id))
            session.commit()

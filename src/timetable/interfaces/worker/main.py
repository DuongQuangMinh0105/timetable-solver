import logging
import os
import time
from pathlib import Path
from uuid import UUID

from timetable.application.use_cases.run_job import RunJob
from timetable.infrastructure.solver.fake import fake_handler
from timetable.infrastructure.storage.local import LocalStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("timetable.worker")


def build_use_case() -> RunJob:
    """Dựng RunJob với Postgres và storage cục bộ.

    Import repository ở đây (không để đầu file) vì database.py cần DATABASE_URL ngay khi import.
    """
    from timetable.infrastructure.persistence.job_repository import JobRepository

    storage = LocalStorage(Path(os.getenv("STORAGE_DIR", "data/storage")))
    return RunJob(JobRepository(), storage, fake_handler)


def main() -> None:
    """Có JOB_ID: chạy job rồi thoát (lỗi thì thoát với mã khác 0). Không có: chờ (compose)."""
    raw_job_id = os.getenv("JOB_ID")
    logger.info("Worker started. JOB_ID=%s", raw_job_id or "<none>")
    if raw_job_id:
        job = build_use_case().execute(UUID(raw_job_id))
        logger.info("Job %s finished with status %s", job.id, job.status.value)
        return
    while True:
        time.sleep(30)


if __name__ == "__main__":
    main()

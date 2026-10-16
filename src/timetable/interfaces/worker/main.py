import logging
import os
import time
from uuid import UUID

from timetable.application.use_cases.run_job import RunJob
from timetable.domain.services.timetable_checker import check_timetable
from timetable.infrastructure.solver.default_solver import build_default_solver
from timetable.infrastructure.solver.solve_handler import make_solve_handler
from timetable.infrastructure.storage.factory import create_storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("timetable.worker")

IDLE_SLEEP_SECONDS = 3600


def build_use_case() -> RunJob:
    """Dựng RunJob với Postgres, storage (theo STORAGE_BACKEND) và bộ giải CP-SAT thật.

    Import repository ở đây (không để đầu file) vì database.py cần
    DATABASE_URL ngay khi import.
    """
    from timetable.infrastructure.persistence.job_repository import JobRepository

    storage = create_storage()
    handler = make_solve_handler(build_default_solver, check_timetable)
    return RunJob(JobRepository(), storage, handler)


def wait_forever() -> None:
    """Giữ container sống khi chạy compose mà chưa có job cụ thể."""
    while True:
        time.sleep(IDLE_SLEEP_SECONDS)


def main() -> None:
    """Có JOB_ID: chạy job rồi thoát (lỗi thì thoát với mã khác 0).

    Không có JOB_ID: chờ (compose).
    """
    raw_job_id = os.getenv("JOB_ID")
    logger.info("Worker started. JOB_ID=%s", raw_job_id or "<none>")

    if not raw_job_id:
        wait_forever()
        return

    try:
        job = build_use_case().execute(UUID(raw_job_id))
    except Exception:
        logger.exception("Job %s failed.", raw_job_id)
        raise SystemExit(1) from None

    logger.info("Job %s finished with status %s", job.id, job.status.value)


if __name__ == "__main__":
    main()

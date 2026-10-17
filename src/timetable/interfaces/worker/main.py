import logging
import os
from uuid import UUID

from redis import Redis

from timetable.application.use_cases.run_job import RunJob
from timetable.domain.services.timetable_checker import check_timetable
from timetable.infrastructure.persistence.job_repository import JobRepository
from timetable.infrastructure.solver.default_solver import build_default_solver
from timetable.infrastructure.solver.solve_handler import make_solve_handler
from timetable.infrastructure.storage.factory import create_storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("timetable.worker")

QUEUE_NAME = os.getenv("QUEUE_NAME", "timetable:jobs")
QUEUE_WAIT_SECONDS = 5


def build_use_case() -> RunJob:
    """Build RunJob with repository, configured storage and real solver."""
    storage = create_storage()
    handler = make_solve_handler(build_default_solver, check_timetable)

    return RunJob(
        repository=JobRepository(),
        storage=storage,
        handler=handler,
    )


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_timeout=QUEUE_WAIT_SECONDS + 5,
        socket_connect_timeout=5,
    )
    use_case = build_use_case()

    logger.info("Worker started. Waiting for jobs on queue %s", QUEUE_NAME)

    try:
        while True:
            item = redis_client.brpop(QUEUE_NAME, timeout=QUEUE_WAIT_SECONDS)

            if item is None:
                continue

            _, raw_job_id = item

            try:
                if isinstance(raw_job_id, bytes):
                    raw_job_id = raw_job_id.decode("utf-8")
                job_id = UUID(raw_job_id)
                job = use_case.execute(job_id)
                logger.info(
                    "Job %s finished with status %s",
                    job.id,
                    job.status.value,
                )
            except Exception:
                logger.exception("Failed to process job %s", raw_job_id)
    finally:
        redis_client.close()


if __name__ == "__main__":
    main()

import logging
import os
import time
from uuid import UUID

from redis import Redis

from timetable.application.use_cases.reconcile_queued_jobs import (
    ReconcileQueuedJobs,
)
from timetable.application.use_cases.run_job import RunJob
from timetable.domain.services.timetable_checker import check_timetable
from timetable.infrastructure.dispatch.redis import RedisJobDispatcher
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
RECONCILE_INTERVAL_SECONDS = 30
RECONCILE_BATCH_SIZE = 100


def build_use_case() -> RunJob:
    """Build RunJob with repository, configured storage and real solver."""
    storage = create_storage()
    handler = make_solve_handler(build_default_solver, check_timetable)

    return RunJob(
        repository=JobRepository(),
        storage=storage,
        handler=handler,
    )


def build_reconciler() -> ReconcileQueuedJobs:
    """Build the use case that retries dispatching queued jobs."""
    return ReconcileQueuedJobs(
        repository=JobRepository(),
        dispatcher=RedisJobDispatcher(queue_name=QUEUE_NAME),
        batch_size=RECONCILE_BATCH_SIZE,
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
    reconciler = build_reconciler()
    next_reconcile_at = 0.0

    logger.info("Worker started. Waiting for jobs on queue %s", QUEUE_NAME)

    try:
        while True:
            now = time.monotonic()

            if now >= next_reconcile_at:
                try:
                    result = reconciler.execute()
                    logger.info(
                        "Queue reconciliation: scanned=%s dispatched=%s failed=%s",
                        result.scanned,
                        result.dispatched,
                        result.failed,
                    )
                except Exception:
                    logger.exception("Queue reconciliation failed")

                next_reconcile_at = time.monotonic() + RECONCILE_INTERVAL_SECONDS

            try:
                item = redis_client.brpop(
                    QUEUE_NAME,
                    timeout=QUEUE_WAIT_SECONDS,
                )
            except Exception:
                logger.exception("Redis queue read failed")
                time.sleep(1)
                continue

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

import json
import logging
import os
from pathlib import Path
from uuid import UUID
import time
from pathlib import Path
from uuid import UUID

from timetable.application.use_cases.run_job import RunJob
from timetable.infrastructure.solver.fake import fake_handler
from timetable.infrastructure.storage.local import LocalStorage

from timetable.application.use_cases.solve_timetable import SolveTimetable
from timetable.domain.entities.job import JobStatus
from timetable.domain.services.timetable_checker import check_timetable
from timetable.infrastructure.persistence.job_repository import JobRepository
from timetable.infrastructure.problem_loader import (
    problem_from_dict,
    solve_options_from_dict,
)
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.storage.local import LocalStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("timetable.worker")


def process_job(job_id: UUID) -> None:
    repository = JobRepository()
    storage = LocalStorage(Path(os.getenv("STORAGE_ROOT", "var/storage")))

    job = repository.get_by_id(job_id)
    if job is None:
        raise LookupError(f"Job {job_id} does not exist.")

    if job.status != JobStatus.QUEUED:
        logger.warning(
            "Skip job %s because its status is %s.",
            job_id,
            job.status.value,
        )
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

    job.status = JobStatus.RUNNING
    repository.update(job)

    try:
        payload = json.loads(storage.get(job.input_ref).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Job input must be a JSON object.")

        problem = problem_from_dict(payload)
        options = solve_options_from_dict(payload)

        use_case = SolveTimetable(
            solver=CpSatSolver(),
            checker=check_timetable,
        )
        outcome = use_case.execute(problem, options)
        result = outcome.result
        timetable = result.timetable

        result_payload: dict[str, object] = {
            "solver_status": result.status.value,
            "valid": outcome.ok,
            "objective": result.objective,
            "cost_terms": result.cost_terms,
            "violations": [
                {
                    "rule_id": violation.rule_id,
                    "description": violation.description,
                }
                for violation in outcome.violations
            ],
            "timetable": (
                None
                if timetable is None
                else {
                    "assignments": [
                        {
                            "unit_id": assignment.unit_id,
                            "day": assignment.day,
                            "period": assignment.period,
                            "room_id": assignment.room_id,
                        }
                        for assignment in timetable.assignments
                    ]
                }
            ),
        }

        result_ref = f"results/{job_id}.json"
        storage.put(
            result_ref,
            json.dumps(result_payload, ensure_ascii=False).encode("utf-8"),
        )

        job.result_ref = result_ref
        job.status = JobStatus.COMPLETED
        repository.update(job)

        logger.info(
            "Job %s completed with solver status %s.",
            job_id,
            result.status.value,
        )

    except Exception:
        logger.exception("Job %s failed.", job_id)
        job.status = JobStatus.FAILED
        try:
            repository.update(job)
        except Exception:
            logger.exception("Could not mark job %s as FAILED.", job_id)
        raise


def main() -> None:
    raw_job_id = os.getenv("JOB_ID")
    if not raw_job_id:
        logger.error("JOB_ID is missing.")
        raise SystemExit(2)

    try:
        process_job(UUID(raw_job_id))
    except Exception:
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
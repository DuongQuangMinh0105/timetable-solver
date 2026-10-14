import os
from pathlib import Path

from timetable.application.use_cases.submit_solve_job import SubmitSolveJob


def create_submit_solve_job() -> SubmitSolveJob:
    """Build the dependencies required to submit a solve job."""
    # Import infrastructure lazily so importing the API does not
    # immediately initialize the database engine.
    from timetable.infrastructure.dispatch.local import LocalJobDispatcher
    from timetable.infrastructure.persistence.job_repository import JobRepository
    from timetable.infrastructure.storage.local import LocalStorage

    # Dùng chung biến STORAGE_DIR với worker để API và worker cùng nhìn một thư mục.
    storage_root = Path(os.getenv("STORAGE_DIR", "data/storage"))

    return SubmitSolveJob(
        repository=JobRepository(),
        storage=LocalStorage(storage_root),
        dispatcher=LocalJobDispatcher(),
    )

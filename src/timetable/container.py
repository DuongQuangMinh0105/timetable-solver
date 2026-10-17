
from timetable.application.use_cases.get_job import GetJob
from timetable.application.use_cases.submit_solve_job import SubmitSolveJob


def create_submit_solve_job() -> SubmitSolveJob:
    """Build the dependencies required to submit a solve job."""
    # Import infrastructure lazily so importing the API does not
    # immediately initialize the database engine.
    from timetable.infrastructure.dispatch.redis import RedisJobDispatcher
    from timetable.infrastructure.persistence.job_repository import JobRepository
    from timetable.infrastructure.storage.factory import create_storage

    return SubmitSolveJob(
        repository=JobRepository(),
        storage=create_storage(),
        dispatcher=RedisJobDispatcher(),
    )


def create_get_job() -> GetJob:
    """Build the dependencies required to read a job."""
    from timetable.infrastructure.persistence.job_repository import JobRepository

    return GetJob(repository=JobRepository())
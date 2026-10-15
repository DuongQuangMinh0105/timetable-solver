from timetable.application.use_cases.get_job import GetJob
from timetable.application.use_cases.submit_solve_job import SubmitSolveJob
from timetable.container import create_get_job, create_submit_solve_job


def get_get_job() -> GetJob:
    """Provide the use case for getting a job."""
    return create_get_job()


def get_submit_solve_job() -> SubmitSolveJob:
    """Provide the use case for the solve endpoint."""
    return create_submit_solve_job()

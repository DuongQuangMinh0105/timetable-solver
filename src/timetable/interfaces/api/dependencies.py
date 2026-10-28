from timetable.application.use_cases.edited_result import (
    GetEditedResult,
    SaveEditedResult,
    ValidateEditedResult,
)
from timetable.application.use_cases.get_job import GetJob
from timetable.application.use_cases.get_job_result import GetJobResult
from timetable.application.use_cases.submit_solve_job import SubmitSolveJob
from timetable.container import (
    create_get_edited_result,
    create_get_job,
    create_get_job_result,
    create_save_edited_result,
    create_submit_solve_job,
    create_validate_edited_result,
)


def get_get_job() -> GetJob:
    """Provide the use case for getting a job."""
    return create_get_job()


def get_get_job_result() -> GetJobResult:
    """Provide the use case for reading a job result."""
    return create_get_job_result()


def get_submit_solve_job() -> SubmitSolveJob:
    """Provide the use case for the solve endpoint."""
    return create_submit_solve_job()


def get_validate_edited_result() -> ValidateEditedResult:
    """Provide the use case that validates an edited timetable."""
    return create_validate_edited_result()


def get_save_edited_result() -> SaveEditedResult:
    """Provide the use case that saves an edited timetable."""
    return create_save_edited_result()


def get_get_edited_result() -> GetEditedResult:
    """Provide the use case that reads a saved edited timetable."""
    return create_get_edited_result()

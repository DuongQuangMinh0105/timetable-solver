from timetable.application.use_cases.edited_result import (
    GetEditedResult,
    SaveEditedResult,
    ValidateEditedResult,
)
from timetable.application.use_cases.get_job import GetJob
from timetable.application.use_cases.get_job_result import GetJobResult
from timetable.application.use_cases.submit_solve_job import SubmitSolveJob


def create_submit_solve_job() -> SubmitSolveJob:
    """Build the dependencies required to submit a solve job."""
    # Import infrastructure lazily so importing the API does not
    # immediately initialize the database engine.
    from timetable.infrastructure.dispatch.factory import create_dispatcher
    from timetable.infrastructure.persistence.job_repository import JobRepository
    from timetable.infrastructure.storage.factory import create_storage

    return SubmitSolveJob(
        repository=JobRepository(),
        storage=create_storage(),
        dispatcher=create_dispatcher(),
    )


def create_get_job() -> GetJob:
    """Build the dependencies required to read a job."""
    from timetable.infrastructure.persistence.job_repository import JobRepository

    return GetJob(repository=JobRepository())


def create_get_job_result() -> GetJobResult:
    """Build the dependencies required to read a job result."""
    from timetable.infrastructure.persistence.job_repository import JobRepository
    from timetable.infrastructure.storage.factory import create_storage

    return GetJobResult(repository=JobRepository(), storage=create_storage())


def create_validate_edited_result() -> ValidateEditedResult:
    """Build the dependencies required to validate a manually edited timetable."""
    from timetable.infrastructure.persistence.job_repository import JobRepository
    from timetable.infrastructure.problem_loader import problem_from_dict
    from timetable.infrastructure.storage.factory import create_storage

    return ValidateEditedResult(JobRepository(), create_storage(), problem_from_dict)


def create_save_edited_result() -> SaveEditedResult:
    """Build the dependencies required to save a manually edited timetable."""
    from timetable.infrastructure.persistence.job_repository import JobRepository
    from timetable.infrastructure.problem_loader import problem_from_dict
    from timetable.infrastructure.storage.factory import create_storage

    return SaveEditedResult(JobRepository(), create_storage(), problem_from_dict)


def create_get_edited_result() -> GetEditedResult:
    """Build the dependencies required to read a saved edited timetable."""
    from timetable.infrastructure.persistence.job_repository import JobRepository
    from timetable.infrastructure.storage.factory import create_storage

    return GetEditedResult(JobRepository(), create_storage())

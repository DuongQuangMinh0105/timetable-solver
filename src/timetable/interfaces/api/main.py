from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Security, status

from timetable.application.use_cases.get_job import GetJob, JobNotFoundError
from timetable.application.use_cases.get_job_result import GetJobResult, ResultNotReadyError
from timetable.application.use_cases.submit_solve_job import SubmitSolveJob
from timetable.interfaces.api.dependencies import (
    get_get_job,
    get_get_job_result,
    get_submit_solve_job,
)
from timetable.interfaces.api.schemas.job_response import JobResponse
from timetable.interfaces.api.schemas.solve import SolveRequest
from timetable.interfaces.api.schemas.solve_response import SolveAcceptedResponse
from timetable.interfaces.api.security import verify_api_key

app = FastAPI(
    title="Timetable Solver API",
    version="0.1.0",
    description=(
        "API for submitting timetable-solving jobs and checking their status. "
        "Protected endpoints require an X-API-Key header."
    ),
)


@app.get(
    "/health",
    tags=["Health"],
    summary="Check API health",
    response_description="API health status",
)
def health_check() -> dict[str, str]:
    """Return the API health status."""
    return {"status": "healthy"}


@app.post(
    "/solve",
    response_model=SolveAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Solve"],
    summary="Submit a timetable-solving job",
    description="Submit a timetable problem. A job is queued for processing.",
    dependencies=[Security(verify_api_key)],
    responses={
        202: {
            "description": "Solve job accepted",
            "content": {
                "application/json": {
                    "example": {
                        "status": "queued",
                        "job_id": "123e4567-e89b-12d3-a456-426614174000",
                    }
                }
            },
        },
        401: {
            "description": "API key is missing or invalid",
            "content": {"application/json": {"example": {"detail": "Invalid or missing API key"}}},
        },
        422: {
            "description": "Request validation failed",
        },
    },
)
def submit_solve(
    request: SolveRequest,
    use_case: Annotated[
        SubmitSolveJob,
        Depends(get_submit_solve_job),
    ],
) -> SolveAcceptedResponse:
    """Accept a timetable solve request and queue a job."""
    result = use_case.execute(request.model_dump(mode="json"))

    return SolveAcceptedResponse(
        job_id=result.job_id,
    )


@app.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    tags=["Jobs"],
    summary="Get job status",
    description="Retrieve the status and result reference for a submitted job.",
    dependencies=[Security(verify_api_key)],
    responses={
        200: {
            "description": "Job details",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "QUEUED",
                        "result_ref": None,
                    }
                }
            },
        },
        401: {
            "description": "API key is missing or invalid",
            "content": {"application/json": {"example": {"detail": "Invalid or missing API key"}}},
        },
        404: {
            "description": "Job not found",
            "content": {"application/json": {"example": {"detail": "Job not found"}}},
        },
        422: {
            "description": "Invalid job ID",
        },
    },
)
def get_job(
    job_id: UUID,
    use_case: Annotated[GetJob, Depends(get_get_job)],
) -> JobResponse:
    """Return the status of a job."""
    try:
        job = use_case.execute(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        ) from exc

    api_status = "DONE" if job.status.value == "completed" else job.status.value.upper()

    return JobResponse(
        job_id=job.id,
        status=api_status,
        result_ref=job.result_ref,
    )


@app.get(
    "/jobs/{job_id}/result",
    tags=["Jobs"],
    summary="Get job result",
    description="Return the result.json of a finished job (status, assignments, violations).",
    dependencies=[Security(verify_api_key)],
    responses={
        401: {"description": "API key is missing or invalid"},
        404: {"description": "Job not found"},
        409: {"description": "Result is not ready"},
    },
)
def get_job_result(
    job_id: UUID,
    use_case: Annotated[GetJobResult, Depends(get_get_job_result)],
) -> dict[str, Any]:
    """Return the result of a finished job."""
    try:
        return use_case.execute(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    except ResultNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Result is not ready"
        ) from exc

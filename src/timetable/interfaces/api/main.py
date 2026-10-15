from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status

from timetable.application.use_cases.get_job import GetJob, JobNotFoundError
from timetable.application.use_cases.submit_solve_job import SubmitSolveJob
from timetable.interfaces.api.dependencies import get_get_job, get_submit_solve_job
from timetable.interfaces.api.schemas.job_response import JobResponse
from timetable.interfaces.api.schemas.solve import SolveRequest
from timetable.interfaces.api.schemas.solve_response import SolveAcceptedResponse

app = FastAPI(
    title="Timetable Solver API",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Return the API health status."""
    return {"status": "healthy"}


@app.post(
    "/solve",
    response_model=SolveAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Solve"],
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
)
def get_job(
    job_id: UUID,
    use_case: Annotated[GetJob, Depends(get_get_job)],
) -> JobResponse:
    try:
        job = use_case.execute(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    api_status = "DONE" if job.status.value == "completed" else job.status.value.upper()

    return JobResponse(
        job_id=job.id,
        status=api_status,
        result_ref=job.result_ref,
    )

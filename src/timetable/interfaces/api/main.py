from typing import Annotated

from fastapi import Depends, FastAPI, status

from timetable.application.use_cases.submit_solve_job import SubmitSolveJob
from timetable.interfaces.api.dependencies import get_submit_solve_job
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

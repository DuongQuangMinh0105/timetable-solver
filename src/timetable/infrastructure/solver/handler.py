import json
from collections.abc import Callable
from typing import Any

from timetable.application.dto.solve_request import SolveRequest
from timetable.infrastructure.problem_loader import (
    problem_from_dict,
    solve_options_from_dict,
)
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver


def create_solver_handler(
    solver: CpSatSolver | None = None,
) -> Callable[[bytes], bytes]:
    """Táº¡o handler chuyá»ƒn JSON input thÃ nh bÃ i toÃ¡n vÃ  cháº¡y CP-SAT."""
    solver_instance = solver or CpSatSolver()

    def handle(data: bytes) -> bytes:
        raw: Any = json.loads(data.decode("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Input JSON pháº£i lÃ  má»™t object")

        # Validate payload theo schema API.
        request = SolveRequest.model_validate(raw)
        payload = request.model_dump(mode="json")

        # Chuyá»ƒn payload thÃ nh domain model vÃ  solver options.
        problem = problem_from_dict(payload)
        options = solve_options_from_dict(payload)

        result = solver_instance.solve(problem, options)

        # Xá»­ lÃ½ an toÃ n cho trÆ°á»ng há»£p result.timetable lÃ  None
        timetable_data = None
        if result.timetable is not None and hasattr(result.timetable, "assignments"):
            timetable_data = [
                {
                    "unit_id": assignment.unit_id,
                    "day": assignment.day,
                    "period": assignment.period,
                    "room_id": assignment.room_id,
                }
                for assignment in result.timetable.assignments
            ]

        # Serialize káº¿t quáº£ thÃ nh JSON bytes Ä‘á»ƒ RunJob lÆ°u vÃ o storage.
        output = {
            "status": result.status.value,
            "optimal": result.optimal,
            "objective": result.objective,
            "objective_bound": result.objective_bound,
            "cost_terms": result.cost_terms,
            "timetable": timetable_data,
        }

        return json.dumps(
            output,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

    return handle

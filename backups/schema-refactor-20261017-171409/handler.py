import json
from collections.abc import Callable
from typing import Any

from timetable.infrastructure.problem_loader import (
    problem_from_dict,
    solve_options_from_dict,
)
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.interfaces.api.schemas.solve import SolveRequest


def create_solver_handler(
    solver: CpSatSolver | None = None,
) -> Callable[[bytes], bytes]:
    """Tạo handler chuyển JSON input thành bài toán và chạy CP-SAT."""
    solver_instance = solver or CpSatSolver()

    def handle(data: bytes) -> bytes:
        raw: Any = json.loads(data.decode("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Input JSON phải là một object")

        # Validate payload theo schema API.
        request = SolveRequest.model_validate(raw)
        payload = request.model_dump(mode="json")

        # Chuyển payload thành domain model và solver options.
        problem = problem_from_dict(payload)
        options = solve_options_from_dict(payload)

        result = solver_instance.solve(problem, options)

        # Xử lý an toàn cho trường hợp result.timetable là None
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

        # Serialize kết quả thành JSON bytes để RunJob lưu vào storage.
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

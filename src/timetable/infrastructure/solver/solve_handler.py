import json
from typing import Any

from timetable.application.ports.solver import SolverPort
from timetable.application.ports.timetable_checker import TimetableChecker
from timetable.application.use_cases.run_job import JobHandler
from timetable.application.use_cases.solve_timetable import SolveOutcome, SolveTimetable
from timetable.infrastructure.problem_loader import problem_from_dict, solve_options_from_dict


class InvalidTimetableError(Exception):
    """Bộ giải trả về lịch nhưng bộ kiểm tra độc lập tìm thấy vi phạm (nghi ngờ mô hình sai)."""


def outcome_to_dict(outcome: SolveOutcome) -> dict[str, Any]:
    """Chuyển kết quả giải thành dict JSON để ghi vào storage."""
    result = outcome.result
    assignments = (
        []
        if result.timetable is None
        else [
            {"unit_id": a.unit_id, "day": a.day, "period": a.period, "room_id": a.room_id}
            for a in result.timetable.assignments
        ]
    )
    return {
        "status": result.status.value,
        "ok": outcome.ok,
        "objective": result.objective,
        "cost_terms": result.cost_terms,
        "assignments": assignments,
        "violations": [
            {"rule_id": v.rule_id, "severity": v.severity, "description": v.description}
            for v in outcome.violations
        ],
    }


def make_solve_handler(solver: SolverPort, checker: TimetableChecker) -> JobHandler:
    """Tạo handler cho RunJob: bytes JSON đầu vào -> giải -> bytes JSON kết quả.

    - Không có lời giải (INFEASIBLE, UNKNOWN...) vẫn là kết quả hợp lệ: ghi vào JSON, job completed.
    - Có lịch nhưng vi phạm ràng buộc cứng thì ném InvalidTimetableError (job failed),
      để lịch sai không bao giờ được lưu như kết quả hợp lệ.
    """

    def handler(data: bytes) -> bytes:
        payload = json.loads(data)
        problem = problem_from_dict(payload)
        options = solve_options_from_dict(payload)
        outcome = SolveTimetable(solver, checker).execute(problem, options)
        if outcome.violations:
            summary = "; ".join(f"{v.rule_id}: {v.description}" for v in outcome.violations[:5])
            raise InvalidTimetableError(f"{len(outcome.violations)} vi phạm. {summary}")
        return json.dumps(outcome_to_dict(outcome), ensure_ascii=False).encode("utf-8")

    return handler

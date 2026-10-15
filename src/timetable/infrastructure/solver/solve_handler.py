import json
from collections.abc import Callable
from typing import Any

from timetable.application.ports.solver import SolverPort
from timetable.application.ports.timetable_checker import TimetableChecker
from timetable.application.use_cases.run_job import JobHandler
from timetable.application.use_cases.solve_timetable import SolveOutcome, SolveTimetable
from timetable.domain.entities import Problem
from timetable.infrastructure.problem_loader import problem_from_dict, solve_options_from_dict

# Dựng bộ giải cho từng bài toán (cần Problem để biết môn MBA và dữ liệu đầu vào để lấy trọng số).
SolverFactory = Callable[[Problem, dict[str, Any]], SolverPort]


class InvalidTimetableError(Exception):
    """Bộ giải trả về lịch nhưng bộ kiểm tra độc lập tìm thấy vi phạm (nghi ngờ mô hình sai)."""


def outcome_to_dict(problem: Problem, outcome: SolveOutcome) -> dict[str, Any]:
    """Chuyển kết quả giải thành dict JSON để ghi vào storage.

    `start_period` là tiết bắt đầu (tính từ 0); đơn vị học chiếm `duration` tiết liên tiếp từ đó.
    """
    result = outcome.result
    units = {u.id: u for u in problem.lesson_units}
    assignments = []
    if result.timetable is not None:
        for a in result.timetable.assignments:
            unit = units[a.unit_id]
            assignments.append(
                {
                    "unit_id": a.unit_id,
                    "course_id": unit.course_id,
                    "class_id": unit.class_id,
                    "teacher_id": unit.teacher_id,
                    "day": a.day,
                    "start_period": a.period,
                    "duration": unit.duration,
                    "room_id": a.room_id,
                }
            )
    objective = result.objective
    if objective is not None and objective == int(objective):
        objective = int(objective)
    return {
        "status": result.status.value,
        "objective": objective,
        "cost_terms": result.cost_terms,
        "assignments": assignments,
        "violations": [
            {"rule_id": v.rule_id, "description": v.description, "severity": v.severity}
            for v in outcome.violations
        ],
    }


def make_solve_handler(solver_factory: SolverFactory, checker: TimetableChecker) -> JobHandler:
    """Tạo handler cho RunJob: bytes JSON đầu vào -> giải -> bytes JSON kết quả.

    - Không có lời giải (INFEASIBLE, UNKNOWN...) vẫn là kết quả hợp lệ: ghi vào JSON, job completed.
    - Có lịch nhưng vi phạm ràng buộc cứng thì ném InvalidTimetableError (job failed),
      để lịch sai không bao giờ được lưu như kết quả hợp lệ.
    """

    def handler(data: bytes) -> bytes:
        payload = json.loads(data)
        problem = problem_from_dict(payload)
        options = solve_options_from_dict(payload)
        solver = solver_factory(problem, payload)
        outcome = SolveTimetable(solver, checker).execute(problem, options)
        if outcome.violations:
            summary = "; ".join(f"{v.rule_id}: {v.description}" for v in outcome.violations[:5])
            raise InvalidTimetableError(f"{len(outcome.violations)} vi phạm. {summary}")
        return json.dumps(outcome_to_dict(problem, outcome), ensure_ascii=False).encode("utf-8")

    return handler

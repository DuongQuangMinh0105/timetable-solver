from typing import Any

from timetable.application.ports.solver import SolverPort
from timetable.domain.entities import Problem
from timetable.domain.rules.soft_constraints import W_G316, W_ROOM, W_SAT
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.soft_adapter import SoftObjectiveApplier
from timetable.infrastructure.solver.soft_objective import add_soft_objective

# Cấu hình ràng buộc mềm theo hướng dẫn của người viết bộ giải (Minh):
SATURDAYS = (5,)  # lưới 6 ngày (thứ 2 đến thứ 7): ngày 5 là thứ Bảy
MBA_ROOM_ID = "G316"
MBA_ROOM_TYPE = "mba"  # môn có required_room_type này là môn MBA


def _weight(config: dict[str, Any], key: str, default: int) -> int:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or value != int(value):
        raise ValueError(f"soft_weights.{key} phải là số nguyên, nhận được {value!r}")
    return int(value)


def soft_weights_from_dict(data: dict[str, Any]) -> tuple[int, int, int]:
    """Đọc `soft_weights` thành (room, sat, g316); thiếu khóa nào thì dùng mặc định."""
    config = data.get("soft_weights", {})
    return (
        _weight(config, "room_stability", W_ROOM),
        _weight(config, "avoid_saturday", W_SAT),
        _weight(config, "reserve_mba_room", W_G316),
    )


def build_default_solver(problem: Problem, data: dict[str, Any]) -> SolverPort:
    """CP-SAT kèm mục tiêu mềm: tránh thứ Bảy, một phòng cho mỗi môn, để dành G316 cho MBA."""
    mba_course_ids = {c.id for c in problem.courses if c.required_room_type == MBA_ROOM_TYPE}
    objective = SoftObjectiveApplier(
        add_soft_objective,
        saturdays=SATURDAYS,
        mba_course_ids=mba_course_ids,
        mba_room_id=MBA_ROOM_ID,
        weights=soft_weights_from_dict(data),
    )
    return CpSatSolver(objective=objective)

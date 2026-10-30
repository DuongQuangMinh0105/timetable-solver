import json
from pathlib import Path
from typing import Any

from timetable.application.dto.solve import SolveOptions
from timetable.domain.constraint_config import (
    SUPPORTED_CONSTRAINT_CONFIG_VERSIONS,
    unsupported_version_message,
)
from timetable.domain.entities import (
    Assignment,
    ClassGroup,
    Course,
    LessonUnit,
    Problem,
    Room,
    Teacher,
    TimeGrid,
)
from timetable.domain.rules.soft_constraints import parse_soft_weights
from timetable.domain.services.teacher_department import check_teacher_departments
from timetable.domain.services.time_labels import slot_name
from timetable.domain.services.unit_consistency import check_units_match_courses
from timetable.domain.services.unit_splitter import lesson_units_for_course


class InvalidProblemError(ValueError):
    """Dữ liệu đầu vào không nhất quán (ví dụ các ca học không khớp số tiết của môn)."""


def problem_from_dict(data: dict[str, Any]) -> Problem:
    """Dựng `Problem` từ dữ liệu theo schema `docs/schema/input.sample.json`."""
    version = data.get("constraint_config_version")
    if version is not None and version not in SUPPORTED_CONSTRAINT_CONFIG_VERSIONS:
        raise InvalidProblemError(unsupported_version_message(str(version)))

    grid_data = data["grid"]
    periods = grid_data["periods"]
    grid = TimeGrid(
        days=grid_data["days"],
        periods=periods,
        allowed_periods=tuple(grid_data["allowed_periods"]),
        period_times=() if periods != 8 else TimeGrid().period_times,
    )

    courses = tuple(Course(**c) for c in data["courses"])
    if data.get("lesson_units"):
        units = tuple(LessonUnit(**u) for u in data["lesson_units"])
    else:
        units = tuple(u for course in courses for u in lesson_units_for_course(course))

    constraints = data.get("constraints", {})
    block_starts = constraints.get("block_starts")

    try:
        soft_weights = parse_soft_weights(data.get("soft_weights", {}))
    except ValueError as exc:
        raise InvalidProblemError(str(exc)) from exc

    problem = Problem(
        rooms=tuple(
            Room(
                id=r["id"],
                name=r["name"],
                capacity=r["capacity"],
                room_type=r.get("room_type", "standard"),
                also_supports=tuple(r.get("also_supports", ())),
            )
            for r in data["rooms"]
        ),
        teachers=tuple(Teacher(**t) for t in data["teachers"]),
        class_groups=tuple(ClassGroup(**c) for c in data["class_groups"]),
        courses=courses,
        lesson_units=units,
        grid=grid,
        max_consecutive_periods=constraints.get("max_consecutive_periods", 2),
        block_starts=None if block_starts is None else tuple(block_starts),
        soft_weights=soft_weights,  # <-- Truyền vào Problem
        fixed_assignments=_fixed_assignments(data, units, grid, data["rooms"]),
    )

    issues = [*check_units_match_courses(problem), *check_teacher_departments(problem)]
    if issues:
        raise InvalidProblemError("; ".join(f"{x.code}: {x.message}" for x in issues))

    return problem


def _fixed_assignments(
    data: dict[str, Any], units: tuple[LessonUnit, ...], grid: TimeGrid, rooms: list[dict[str, Any]]
) -> tuple[Assignment, ...]:
    """Đọc `fixed_assignments` (ca bị khóa) và kiểm tra tham chiếu, ngày, tiết."""
    unit_ids = {u.id for u in units}
    room_ids = {r["id"] for r in rooms}
    result: list[Assignment] = []
    seen: set[str] = set()
    for item in data.get("fixed_assignments") or []:
        unit_id = item["unit_id"]
        if unit_id not in unit_ids:
            raise InvalidProblemError(f"Ca cố định tham chiếu ca học không tồn tại: {unit_id}.")
        if unit_id in seen:
            raise InvalidProblemError(f"Ca học {unit_id} bị khóa hai lần.")
        seen.add(unit_id)
        if item["room_id"] not in room_ids:
            raise InvalidProblemError(
                f"Ca cố định {unit_id} tham chiếu phòng không tồn tại: {item['room_id']}."
            )
        day, period = item["day"], item["start_period"]
        if not 0 <= day < grid.days or period not in grid.allowed_periods:
            raise InvalidProblemError(
                f"Ca cố định {unit_id} nằm ngoài lưới thời gian ({slot_name(day, period)})."
            )
        result.append(Assignment(unit_id=unit_id, day=day, period=period, room_id=item["room_id"]))
    return tuple(result)


def solve_options_from_dict(data: dict[str, Any]) -> SolveOptions:
    """Đọc `solver` trong dữ liệu đầu vào; thiếu khóa nào dùng mặc định của `SolveOptions`."""
    cfg = data.get("solver", {})
    default = SolveOptions()
    return SolveOptions(
        time_limit_s=cfg.get("time_limit_s", default.time_limit_s),
        num_workers=cfg.get("num_workers", default.num_workers),
        random_seed=cfg.get("random_seed", default.random_seed),
    )


def load_problem(path: Path) -> Problem:
    return problem_from_dict(json.loads(path.read_text(encoding="utf-8")))

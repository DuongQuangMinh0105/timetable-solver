import json
from pathlib import Path
from typing import Any

from timetable.application.dto.solve import SolveOptions
from timetable.domain.constraint_config import (
    SUPPORTED_CONSTRAINT_CONFIG_VERSIONS,
    unsupported_version_message,
)
from timetable.domain.entities import (
    ClassGroup,
    Course,
    LessonUnit,
    Problem,
    Room,
    Teacher,
    TimeGrid,
)
from timetable.domain.rules.soft_constraints import parse_soft_weights
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
    )

    issues = check_units_match_courses(problem)
    if issues:
        raise InvalidProblemError("; ".join(f"{x.code}: {x.message}" for x in issues))

    return problem


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

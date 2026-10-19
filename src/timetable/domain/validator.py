"""Kiểm tra độc lập một thời khóa biểu theo các ràng buộc cứng và mềm."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from timetable.domain.entities import LessonUnit, Problem, Room, Slot, Timetable
from timetable.domain.entities.time_grid import TimeGrid
from timetable.domain.rules.soft_constraints import reference_cost

# (chủ thể, ngày, tiết) -> các unit đang dùng ô đó
Usage = dict[tuple[str, int, int], list[str]]

_ROOM_TYPE_RULES = {"mba": "MBA_ROOM", "art": "ART_ROOM"}


@dataclass
class Violation:
    """Mô tả một lỗi vi phạm quy tắc thời khóa biểu."""

    rule_id: str
    description: str
    severity: str = "HARD"  # "HARD" hoặc "SOFT"


@dataclass
class ValidationSummary:
    """Tóm tắt kết quả kiểm tra cứng và mềm."""

    hard_count: int
    soft_count: int
    total_penalty: int
    hard_violations: list[Violation]
    soft_violations: list[Violation]


def _day_label(day: int) -> str:
    return f"Thứ {day + 2}"


def _longest_run(periods: set[int]) -> int:
    """Độ dài chuỗi tiết liền nhau dài nhất."""
    best = run = 0
    previous: int | None = None
    for p in sorted(periods):
        run = run + 1 if previous is not None and p == previous + 1 else 1
        best = max(best, run)
        previous = p
    return best


def _room_type_violations(unit: LessonUnit, room: Room) -> list[Violation]:
    """Lớp MBA phải ở phòng MBA (G316), lớp vẽ phải ở phòng vẽ (G313).

    Lớp thường ở G316 không phải lỗi cứng: G316 hỗ trợ loại `standard`, và việc
    này chỉ bị phạt mềm (`W_G316`).
    """
    if room.can_host(unit.required_room_type):
        return []
    rule_id = _ROOM_TYPE_RULES.get(unit.required_room_type, "ROOM_TYPE")
    return [
        Violation(
            rule_id,
            f"Unit {unit.id} cần phòng loại {unit.required_room_type} "
            f"nhưng được xếp vào phòng {room.id}.",
        )
    ]


class Validator:
    """Bộ kiểm tra tính hợp lệ của thời khóa biểu dựa trên các domain entities."""

    def validate(self, problem: Problem, timetable: Timetable) -> list[Violation]:
        """Trả về danh sách các vi phạm cứng (rỗng nếu lịch hợp lệ)."""
        if not timetable.assignments:
            return [Violation("TIMETABLE_EMPTY", "Thời khóa biểu không được để trống.")]

        units = {u.id: u for u in problem.lesson_units}
        rooms = {r.id: r for r in problem.rooms}
        violations: list[Violation] = []
        room_use: Usage = defaultdict(list)
        teacher_use: Usage = defaultdict(list)
        class_use: Usage = defaultdict(list)
        class_periods: defaultdict[tuple[str, int], set[int]] = defaultdict(set)

        for a in timetable.assignments:
            unit = units.get(a.unit_id)
            room = rooms.get(a.room_id)
            if unit is None or room is None:
                violations.append(
                    Violation(
                        "UNKNOWN_REFERENCE",
                        f"Phân công {a.unit_id} dùng unit hoặc phòng {a.room_id} không tồn tại.",
                    )
                )
                continue

            occupied = range(a.period, a.period + unit.duration)
            if any(not problem.grid.contains(Slot(a.day, q)) for q in occupied):
                violations.append(
                    Violation(
                        "INVALID_PERIOD",
                        f"Unit {unit.id} ({_day_label(a.day)}, tiết {a.period + 1}, "
                        f"{unit.duration} tiết) nằm ngoài các tiết cho phép.",
                    )
                )
            violations.extend(_room_type_violations(unit, room))

            for q in occupied:
                room_use[a.room_id, a.day, q].append(unit.id)
                teacher_use[unit.teacher_id, a.day, q].append(unit.id)
                class_use[unit.class_id, a.day, q].append(unit.id)
                class_periods[unit.class_id, a.day].add(q)

        for rule_id, label, use in (
            ("ROOM_CONFLICT", "Phòng", room_use),
            ("TEACHER_CONFLICT", "Giáo viên", teacher_use),
            ("CLASS_CONFLICT", "Lớp", class_use),
        ):
            for (owner, day, q), unit_ids in sorted(use.items()):
                if len(unit_ids) > 1:
                    violations.append(
                        Violation(
                            rule_id,
                            f"{label} {owner} bị trùng lịch ở {_day_label(day)}, "
                            f"tiết {q + 1}: {', '.join(unit_ids)}.",
                        )
                    )

        for (class_id, day), periods in sorted(class_periods.items()):
            run = _longest_run(periods)
            if run > problem.max_consecutive_periods:
                violations.append(
                    Violation(
                        "MAX_CONSECUTIVE",
                        f"Lớp {class_id} học {run} tiết liên tiếp ở {_day_label(day)} "
                        f"(tối đa {problem.max_consecutive_periods}).",
                    )
                )

        return violations

    def validate_soft(self, problem: Problem, timetable: Timetable) -> list[Violation]:
        """Tính toán vi phạm mềm dựa trên reference_cost."""
        unit_course = {u.id: u.course_id for u in problem.lesson_units}
        mba_courses = {c.id for c in problem.courses if c.required_room_type == "mba"}
        mba_room = next((r.id for r in problem.rooms if r.room_type == "mba"), "G316")
        sat_days = {TimeGrid.SATURDAY} if problem.grid.days > TimeGrid.SATURDAY else set()

        schedule = [
            (unit_course[a.unit_id], a.day, a.period, a.room_id)
            for a in timetable.assignments
            if a.unit_id in unit_course
        ]

        cost = reference_cost(
            schedule=schedule,
            sat_days=sat_days,
            mba=mba_courses,
            r_mba=mba_room,
            weights=problem.soft_weights,
        )

        violations = []
        if cost["room"] > 0:
            violations.append(
                Violation(
                    rule_id="SOFT_ROOM",
                    description=f"Vi phạm ổn định phòng: {cost['room']} điểm.",
                    severity="SOFT",
                )
            )
        if cost["sat"] > 0:
            violations.append(
                Violation(
                    rule_id="SOFT_SAT",
                    description=f"Vi phạm xếp lịch Thứ 7: {cost['sat']} điểm.",
                    severity="SOFT",
                )
            )
        if cost["g316"] > 0:
            violations.append(
                Violation(
                    rule_id="SOFT_G316",
                    description=f"Vi phạm sử dụng phòng G316: {cost['g316']} điểm.",
                    severity="SOFT",
                )
            )

        return violations


def summarize_validation(problem: Problem, timetable: Timetable) -> ValidationSummary:
    """Chạy cả kiểm tra cứng và mềm, trả về bản tóm tắt."""
    validator = Validator()
    hard_v = validator.validate(problem, timetable)
    soft_v = validator.validate_soft(problem, timetable)

    # Tính tổng điểm phạt trực tiếp từ reference_cost để đảm bảo độc lập
    unit_course = {u.id: u.course_id for u in problem.lesson_units}
    mba_courses = {c.id for c in problem.courses if c.required_room_type == "mba"}
    mba_room = next((r.id for r in problem.rooms if r.room_type == "mba"), "G316")
    sat_days = {TimeGrid.SATURDAY} if problem.grid.days > TimeGrid.SATURDAY else set()

    schedule = [
        (unit_course[a.unit_id], a.day, a.period, a.room_id)
        for a in timetable.assignments
        if a.unit_id in unit_course
    ]
    cost = reference_cost(schedule, sat_days, mba_courses, mba_room, problem.soft_weights)
    total_penalty = sum(cost.values())

    return ValidationSummary(
        hard_count=len(hard_v),
        soft_count=len(soft_v),
        total_penalty=total_penalty,
        hard_violations=hard_v,
        soft_violations=soft_v,
    )

"""Báo cáo vi phạm mềm (SOFT) dựa trên reference_cost."""

from __future__ import annotations

from dataclasses import dataclass

from timetable.domain.entities import Problem, Timetable
from timetable.domain.entities.time_grid import TimeGrid
from timetable.domain.rules.soft_constraints import reference_cost
from timetable.domain.violation import Violation  # Import từ file violation.py có sẵn


@dataclass
class ValidationSummary:
    """Tóm tắt kết quả kiểm tra cứng và mềm."""

    hard_count: int
    soft_count: int
    total_penalty: int
    hard_violations: list[Violation]
    soft_violations: list[Violation]


def validate_soft(problem: Problem, timetable: Timetable) -> list[Violation]:
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


def summarize_validation(
    problem: Problem, timetable: Timetable, hard_violations: list[Violation]
) -> ValidationSummary:
    """Tổng hợp kết quả cứng (từ Validator cũ) và mềm (từ validate_soft)."""
    soft_v = validate_soft(problem, timetable)

    # Tính tổng điểm phạt trực tiếp từ reference_cost
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
        hard_count=len(hard_violations),
        soft_count=len(soft_v),
        total_penalty=total_penalty,
        hard_violations=hard_violations,
        soft_violations=soft_v,
    )

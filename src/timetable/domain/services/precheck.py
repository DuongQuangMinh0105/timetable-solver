"""Fast infeasibility pre-checks (pure Python, no solver).

These are loose upper bounds: they only flag cases that are definitely
infeasible, so a clean result does not guarantee a solution exists.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from timetable.domain.entities import Problem
from timetable.domain.services.room_policy import allowed_rooms_by_unit


@dataclass(frozen=True)
class OfferingInfo:
    id: str
    kind: str  # "regular" | "mba" | "design"
    class_size: int
    sessions_per_week: int
    teacher_id: str


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    suggestion: str


def diagnose_problem(problem: Problem) -> list[Issue]:
    """Return only provable capacity/eligibility causes for an infeasible problem."""
    room_options = allowed_rooms_by_unit(problem)
    issues: list[Issue] = []
    units_by_room_type: dict[str, list[str]] = defaultdict(list)
    for unit in problem.lesson_units:
        eligible = room_options[unit.id]
        if not eligible:
            issues.append(
                Issue(
                    "no_eligible_room",
                    f"Unit {unit.id} has no room with the required type and capacity.",
                    "Add a suitable room or reduce the class size.",
                )
            )
        units_by_room_type[unit.required_room_type].append(unit.id)

    # These aggregate bounds ignore clashes between classes and teachers, so they can
    # prove infeasibility without incorrectly rejecting a potentially feasible schedule.
    for room_type, unit_ids in sorted(units_by_room_type.items()):
        eligible_rooms = {room.id for unit_id in unit_ids for room in room_options[unit_id]}
        capacity = len(eligible_rooms) * problem.grid.num_slots
        if eligible_rooms and len(unit_ids) > capacity:
            issues.append(
                Issue(
                    f"{room_type}_room_capacity",
                    f"{len(unit_ids)} {room_type} units exceed the "
                    f"{capacity} available room slots.",
                    "Add suitable rooms or reduce the number of scheduled units.",
                )
            )

    units_by_teacher: dict[str, int] = defaultdict(int)
    for unit in problem.lesson_units:
        units_by_teacher[unit.teacher_id] += 1
    for teacher_id, load in sorted(units_by_teacher.items()):
        if load > problem.grid.num_slots:
            issues.append(
                Issue(
                    "teacher_overload",
                    f"Teacher {teacher_id} needs {load} units, but can use at most "
                    f"{problem.grid.num_slots} slots.",
                    "Reduce this teacher's load or assign another teacher.",
                )
            )

    return issues


def precheck(
    offerings: Iterable[OfferingInfo],
    regular_room_count: int,
    design_room_count: int = 1,
    days: int = 6,
    blocks_per_day: int = 3,
    min_size: int = 20,
    max_size: int = 30,
) -> list[Issue]:
    offerings = list(offerings)
    cap = days * blocks_per_day  # max 2-period blocks per room (or teacher) per week
    issues: list[Issue] = []

    for o in offerings:
        if not (min_size <= o.class_size <= max_size):
            issues.append(
                Issue(
                    "class_size",
                    f"Offering {o.id} has {o.class_size} students, "
                    f"outside the allowed range {min_size}-{max_size}.",
                    "Fix the class size, or split/merge the class.",
                )
            )

    teacher_load: dict[str, int] = defaultdict(int)
    for o in offerings:
        teacher_load[o.teacher_id] += o.sessions_per_week
    for teacher, load in sorted(teacher_load.items()):
        if load > cap:
            issues.append(
                Issue(
                    "teacher_overload",
                    f"Teacher {teacher} needs {load} sessions per week, "
                    f"but at most {cap} can be scheduled.",
                    "Reduce this teacher's load or assign another teacher.",
                )
            )

    mba_total = sum(o.sessions_per_week for o in offerings if o.kind == "mba")
    if mba_total > cap:
        issues.append(
            Issue(
                "mba_capacity",
                f"MBA offerings need {mba_total} sessions per week, "
                f"but room G316 holds at most {cap}.",
                "Reduce the number of MBA sessions or allow MBA in more rooms.",
            )
        )

    design_total = sum(o.sessions_per_week for o in offerings if o.kind == "design")
    design_cap = cap * design_room_count
    if design_total > design_cap:
        issues.append(
            Issue(
                "design_capacity",
                f"Design offerings need {design_total} sessions per week, "
                f"but the design room holds at most {design_cap}.",
                "Reduce the number of Design sessions or add a design room.",
            )
        )

    regular_total = sum(o.sessions_per_week for o in offerings if o.kind != "design")
    regular_cap = cap * regular_room_count
    if regular_total > regular_cap:
        issues.append(
            Issue(
                "total_capacity",
                f"{regular_total} sessions per week exceed the capacity of "
                f"{regular_cap} sessions across {regular_room_count} regular rooms.",
                "Reduce sessions, add rooms, or allow more teaching days.",
            )
        )

    return issues

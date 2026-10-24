"""Fast infeasibility pre-checks (pure Python, no solver).

These are loose upper bounds: they only flag cases that are definitely
infeasible, so a clean result does not guarantee a solution exists.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass


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

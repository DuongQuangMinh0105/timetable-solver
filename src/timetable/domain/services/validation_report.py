from collections import Counter
from collections.abc import Collection
from dataclasses import dataclass
from typing import Any

from timetable.domain.entities import Problem, Timetable
from timetable.domain.rules.soft_constraints import W_G316, W_ROOM, W_SAT
from timetable.domain.services.timetable_checker import check_timetable
from timetable.domain.violation import Violation

SATURDAY = 5  # ngày 0 = Thứ 2 ... 5 = Thứ 7
MBA_ROOM_ID = "G316"
MBA_ROOM_TYPE = "mba"


@dataclass(frozen=True, slots=True)
class SoftViolation:
    """Một điểm phạt của ràng buộc mềm (không làm lịch sai, chỉ làm lịch kém hơn)."""

    rule_id: str
    description: str
    penalty: int


def soft_violations(
    problem: Problem,
    timetable: Timetable,
    sat_days: Collection[int] = (SATURDAY,),
    mba_room_id: str = MBA_ROOM_ID,
    weights: tuple[int, int, int] = (W_ROOM, W_SAT, W_G316),
) -> list[SoftViolation]:
    """Liệt kê điểm phạt mềm của một lịch.

    Gồm ba loại: học thứ Bảy, đổi phòng giữa các tiết của một môn, và dùng G316 cho môn
    không phải MBA.
    """
    w_room, w_sat, w_g316 = weights
    units = {u.id: u for u in problem.lesson_units}
    mba_courses = {c.id for c in problem.courses if c.required_room_type == MBA_ROOM_TYPE}
    rooms_of: dict[str, set[str]] = {}
    out: list[SoftViolation] = []

    for a in timetable.assignments:
        unit = units.get(a.unit_id)
        if unit is None:
            continue
        rooms_of.setdefault(unit.course_id, set()).add(a.room_id)
        if a.day in sat_days:
            out.append(
                SoftViolation("AVOID_SATURDAY", f"{unit.id} học vào ngày {a.day} (Thứ 7).", w_sat)
            )
        if a.room_id == mba_room_id and unit.course_id not in mba_courses:
            out.append(
                SoftViolation(
                    "RESERVE_MBA_ROOM",
                    f"{unit.id} (môn không phải MBA) dùng phòng {mba_room_id}.",
                    w_g316,
                )
            )
    for course_id, rooms in sorted(rooms_of.items()):
        if len(rooms) > 1:
            out.append(
                SoftViolation(
                    "ROOM_STABILITY",
                    f"Môn {course_id} học ở {len(rooms)} phòng khác nhau.",
                    w_room * (len(rooms) - 1),
                )
            )
    return out


@dataclass(frozen=True, slots=True)
class ValidationReport:
    hard: tuple[Violation, ...]
    soft: tuple[SoftViolation, ...]

    def summary(self) -> dict[str, Any]:
        by_rule: Counter[str] = Counter(v.rule_id for v in self.hard)
        by_rule.update(v.rule_id for v in self.soft)
        return {
            "total": len(self.hard) + len(self.soft),
            "hard": len(self.hard),
            "soft": len(self.soft),
            "soft_penalty": sum(v.penalty for v in self.soft),
            "by_rule": dict(sorted(by_rule.items())),
        }


def build_report(
    problem: Problem,
    timetable: Timetable,
    sat_days: Collection[int] = (SATURDAY,),
    mba_room_id: str = MBA_ROOM_ID,
    weights: tuple[int, int, int] = (W_ROOM, W_SAT, W_G316),
) -> ValidationReport:
    return ValidationReport(
        hard=tuple(check_timetable(problem, timetable)),
        soft=tuple(soft_violations(problem, timetable, sat_days, mba_room_id, weights)),
    )

from collections import defaultdict

from timetable.domain.entities import Problem, Timetable
from timetable.domain.services.slot_policy import allowed_starts
from timetable.domain.violation import Violation


def longest_run(periods: list[int]) -> int:
    """Độ dài chuỗi tiết liền nhau dài nhất trong danh sách chỉ số tiết."""
    best = run = 0
    previous: int | None = None
    for p in sorted(periods):
        run = run + 1 if previous is not None and p == previous + 1 else 1
        best = max(best, run)
        previous = p
    return best


def check_timetable(problem: Problem, timetable: Timetable) -> list[Violation]:
    """Kiểm tra độc lập (không dùng mô hình CP-SAT) các ràng buộc cứng của một thời khóa biểu.

    Trả về danh sách vi phạm; rỗng nghĩa là lịch hợp lệ. `Assignment.period` là tiết bắt đầu và
    đơn vị học chiếm `duration` tiết liên tiếp từ đó.
    """
    violations: list[Violation] = []

    def bad(rule_id: str, description: str) -> None:
        violations.append(Violation(rule_id=rule_id, description=description))

    units = {u.id: u for u in problem.lesson_units}
    rooms = {r.id: r for r in problem.rooms}
    classes = {c.id: c for c in problem.class_groups}

    seen: set[str] = set()
    used: dict[str, dict[tuple[str, int, int], str]] = {"room": {}, "teacher": {}, "class": {}}
    class_periods: dict[tuple[str, int], list[int]] = defaultdict(list)

    for a in timetable.assignments:
        unit = units.get(a.unit_id)
        room = rooms.get(a.room_id)
        if unit is None or room is None:
            bad("UNKNOWN_REFERENCE", f"Phân công tham chiếu id không tồn tại: {a}")
            continue
        if a.unit_id in seen:
            bad("UNIT_DUPLICATED", f"Đơn vị {unit.id} được xếp nhiều lần.")
        seen.add(a.unit_id)

        starts = {(s.day, s.period) for s in allowed_starts(problem, unit)}
        if (a.day, a.period) not in starts:
            bad(
                "INVALID_SLOT",
                f"{unit.id} bắt đầu ở ô không hợp lệ (ngày {a.day}, tiết {a.period}).",
            )
        if not room.can_host(unit.required_room_type):
            bad("ROOM_TYPE", f"Phòng {room.id} không phù hợp loại phòng của {unit.id}.")
        if room.capacity < classes[unit.class_id].size:
            bad("ROOM_CAPACITY", f"Phòng {room.id} không đủ chỗ cho lớp {unit.class_id}.")

        for q in range(a.period, a.period + unit.duration):
            for kind, owner in (
                ("room", room.id),
                ("teacher", unit.teacher_id),
                ("class", unit.class_id),
            ):
                key = (owner, a.day, q)
                if key in used[kind]:
                    bad(
                        f"{kind.upper()}_OVERLAP",
                        f"Trùng {kind} {owner} ở ngày {a.day}, tiết {q}: "
                        f"{used[kind][key]} và {unit.id}.",
                    )
                used[kind][key] = unit.id
            class_periods[(unit.class_id, a.day)].append(q)

    for unit_id in sorted(set(units) - seen):
        bad("UNIT_UNASSIGNED", f"Đơn vị {unit_id} chưa được xếp.")

    for (class_id, day), periods in sorted(class_periods.items()):
        if longest_run(periods) > problem.max_consecutive_periods:
            bad(
                "MAX_CONSECUTIVE",
                f"Lớp {class_id} học quá {problem.max_consecutive_periods} tiết liên tiếp "
                f"ở ngày {day}.",
            )
    return violations

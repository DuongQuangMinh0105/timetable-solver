from collections import defaultdict

from timetable.domain.entities import Problem, Timetable
from timetable.domain.services.slot_policy import allowed_starts
from timetable.domain.services.time_labels import day_name, slot_name
from timetable.domain.violation import Violation


def longest_run(periods: list[int]) -> int:
    """Độ dài chuỗi tiết liền nhau dài nhất trong danh sách chỉ số tiết."""
    best = run = 0
    previous: int | None = None

    for period in sorted(periods):
        run = run + 1 if previous is not None and period == previous + 1 else 1
        best = max(best, run)
        previous = period

    return best


def check_timetable(problem: Problem, timetable: Timetable) -> list[Violation]:
    """Kiểm tra độc lập các ràng buộc cứng của thời khóa biểu.

    Trả về danh sách vi phạm; danh sách rỗng nghĩa là lịch hợp lệ.
    Assignment.period là tiết bắt đầu; đơn vị học chiếm duration tiết liên tiếp.
    """
    violations: list[Violation] = []

    def bad(rule_id: str, description: str) -> None:
        violations.append(Violation(rule_id=rule_id, description=description))

    units = {unit.id: unit for unit in problem.lesson_units}
    rooms = {room.id: room for room in problem.rooms}
    classes = {class_group.id: class_group for class_group in problem.class_groups}

    seen: set[str] = set()

    used: dict[str, dict[tuple[str, int, int], str]] = {
        "room": {},
        "teacher": {},
        "class": {},
    }

    class_periods: dict[tuple[str, int], list[int]] = defaultdict(list)

    for assignment in timetable.assignments:
        unit = units.get(assignment.unit_id)
        room = rooms.get(assignment.room_id)

        if unit is None or room is None:
            bad(
                "UNKNOWN_REFERENCE",
                f"Phân công tham chiếu id không tồn tại: {assignment}",
            )
            continue

        if assignment.unit_id in seen:
            bad(
                "UNIT_DUPLICATED",
                f"Đơn vị {unit.id} được xếp nhiều lần.",
            )

        seen.add(assignment.unit_id)

        starts = {(slot.day, slot.period) for slot in allowed_starts(problem, unit)}

        if (assignment.day, assignment.period) not in starts:
            bad(
                "INVALID_SLOT",
                f"{unit.id} bắt đầu ở ô không hợp lệ "
                f"({slot_name(assignment.day, assignment.period)}).",
            )

        if not room.can_host(unit.required_room_type):
            bad(
                "ROOM_TYPE",
                f"Phòng {room.id} không phù hợp loại phòng của {unit.id}.",
            )

        class_group = classes.get(unit.class_id)
        if class_group is None:
            bad(
                "UNKNOWN_REFERENCE",
                f"Lớp {unit.class_id} của đơn vị {unit.id} không tồn tại.",
            )
            continue

        if room.capacity < class_group.size:
            bad(
                "ROOM_CAPACITY",
                f"Phòng {room.id} không đủ chỗ cho lớp {unit.class_id}.",
            )

        for period in range(
            assignment.period,
            assignment.period + unit.duration,
        ):
            for kind, owner in (
                ("room", room.id),
                ("teacher", unit.teacher_id),
                ("class", unit.class_id),
            ):
                key = (owner, assignment.day, period)

                if key in used[kind]:
                    bad(
                        f"{kind.upper()}_OVERLAP",
                        f"Trùng {kind} {owner} vào {slot_name(assignment.day, period)}: "
                        f"{used[kind][key]} và {unit.id}.",
                    )

                used[kind][key] = unit.id

            class_periods[(unit.class_id, assignment.day)].append(period)

    for unit_id in sorted(set(units) - seen):
        bad(
            "UNIT_UNASSIGNED",
            f"Đơn vị {unit_id} chưa được xếp.",
        )

    for (class_id, day), periods in sorted(class_periods.items()):
        if longest_run(periods) > problem.max_consecutive_periods:
            bad(
                "MAX_CONSECUTIVE",
                f"Lớp {class_id} học quá "
                f"{problem.max_consecutive_periods} tiết liên tiếp vào {day_name(day)}.",
            )

    return violations

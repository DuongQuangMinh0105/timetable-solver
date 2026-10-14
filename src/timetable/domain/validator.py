from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Violation:
    """Mô tả một lỗi vi phạm quy tắc thời khóa biểu."""

    rule_id: str
    description: str
    severity: str = "HARD"  # "HARD" hoặc "SOFT"

    def __hash__(self) -> int:
        return hash((self.rule_id, self.description, self.severity))


def _first(obj: Any, names: tuple[str, ...], default: Any = "") -> Any:
    """Trả về giá trị của thuộc tính đầu tiên tồn tại và khác rỗng."""
    if obj is None:
        return default
    for name in names:
        if isinstance(obj, dict):
            value = obj.get(name)
        else:
            value = getattr(obj, name, None)
        if value not in (None, ""):
            return value
    return default


def _check_max_consecutive(
    label: str,
    owner: str,
    days_map: dict[int, set[int]],
    max_run: int = 2,
) -> list[Violation]:
    """Báo mỗi chuỗi tiết liên tiếp vượt quá max_run đúng một lần."""
    out: list[Violation] = []
    for day, periods in days_map.items():
        sorted_p = sorted(periods)
        run = 1
        flagged = False
        for prev, cur in zip(sorted_p, sorted_p[1:], strict=False):
            if cur == prev + 1:
                run += 1
                if run > max_run and not flagged:
                    out.append(
                        Violation(
                            rule_id="MAX_CONSECUTIVE",
                            description=(
                                f"{label} {owner} có quá {max_run} tiết liên tiếp vào ngày {day}."
                            ),
                            severity="HARD",
                        )
                    )
                    flagged = True
            else:
                run, flagged = 1, False
    return out


class Validator:
    """Bộ kiểm tra tính hợp lệ của thời khóa biểu dựa trên các domain entities và rules."""

    def validate(self, timetable: Any, problem: Any = None) -> list[Violation]:
        """Thực hiện validate thời khóa biểu và trả về danh sách các vi phạm (nếu có)."""
        violations: list[Violation] = []

        # Chuyển đổi timetable sang danh sách chuẩn
        if hasattr(timetable, "assignments"):
            entries = list(timetable.assignments)
        elif isinstance(timetable, list):
            entries = timetable
        else:
            entries = list(timetable) if timetable else []

        # Kiểm tra thời khóa biểu trống
        if not entries:
            violations.append(
                Violation(
                    rule_id="TIMETABLE_EMPTY",
                    description="Thời khóa biểu không được để trống.",
                    severity="HARD",
                )
            )
            return violations

        # Map unit_id với thông tin chi tiết từ problem nếu có
        units_map: dict[str, Any] = {}
        if problem is not None:
            units_source = (
                getattr(problem, "lesson_units", None) or getattr(problem, "units", None) or ()
            )
            for u in units_source:
                units_map[str(_first(u, ("id", "unit_id")))] = u

        # Dùng giới hạn của problem nếu có, mặc định 2
        max_run = int(getattr(problem, "max_consecutive_periods", 2) or 2)

        used_slots: dict[tuple[int, int], dict[str, set[str]]] = {}
        teacher_day_periods: dict[str, dict[int, set[int]]] = {}
        class_day_periods: dict[str, dict[int, set[int]]] = {}

        for entry in entries:
            # Trích xuất unit_id, day, period, room an toàn
            unit_id = str(_first(entry, ("unit_id", "id")))
            day = int(_first(entry, ("day",), 0))
            period = int(_first(entry, ("period",), 0))
            room = str(_first(entry, ("room_id", "room")))

            # Lấy thông tin từ unit trong problem nếu có
            unit_info = units_map.get(unit_id)

            teacher = str(_first(unit_info, ("teacher_id", "teacher")))
            class_group = str(_first(unit_info, ("class_group_id", "class_group", "class_id")))
            subject = str(_first(unit_info, ("subject_id", "subject"), unit_id))
            duration = int(_first(unit_info, ("duration", "length", "periods"), 1))

            # Fallback lấy trực tiếp từ entry nếu unit_info không có
            if not teacher:
                teacher = str(_first(entry, ("teacher_id", "teacher")))
            if not class_group:
                class_group = str(_first(entry, ("class_group_id", "class_group")))
            if subject == unit_id or not subject:
                subject = str(_first(entry, ("subject_id", "subject"), subject))

            for p_offset in range(duration):
                curr_period = period + p_offset
                slot_key = (day, curr_period)

                if teacher:
                    teacher_day_periods.setdefault(teacher, {}).setdefault(day, set()).add(
                        curr_period
                    )

                if class_group:
                    class_day_periods.setdefault(class_group, {}).setdefault(day, set()).add(
                        curr_period
                    )

                slot = used_slots.setdefault(
                    slot_key,
                    {"rooms": set(), "teachers": set(), "classes": set()},
                )

                # Kiểm tra trùng phòng
                if room:
                    if room in slot["rooms"]:
                        violations.append(
                            Violation(
                                rule_id="ROOM_CONFLICT",
                                description=(
                        f"Phòng {room} bị trùng lịch ở ngày {day}, "
                        f"tiết {curr_period}."
                    ),
                                severity="HARD",
                            )
                        )
                    else:
                        slot["rooms"].add(room)

                # Kiểm tra trùng giáo viên
                if teacher:
                    if teacher in slot["teachers"]:
                        violations.append(
                            Violation(
                                rule_id="TEACHER_CONFLICT",
                                description=(
                        f"Phòng {room} bị trùng lịch ở ngày {day}, "
                        f"tiết {curr_period}."
                    ),
                                severity="HARD",
                            )
                        )
                    else:
                        slot["teachers"].add(teacher)

                # Kiểm tra trùng lớp
                if class_group:
                    if class_group in slot["classes"]:
                        violations.append(
                            Violation(
                                rule_id="CLASS_CONFLICT",
                                description=(
                        f"Phòng {room} bị trùng lịch ở ngày {day}, "
                        f"tiết {curr_period}."
                    ),
                                severity="HARD",
                            )
                        )
                    else:
                        slot["classes"].add(class_group)

            # Quy tắc: MBA bắt buộc ở phòng G316
            content_check = (subject + " " + class_group).upper()
            if "MBA" in content_check and room != "G316":
                violations.append(
                    Violation(
                        rule_id="MBA_ROOM_VIOLATION",
                        description=f"Môn/Lớp MBA phải được xếp ở phòng G316, hiện tại ở {room}.",
                        severity="HARD",
                    )
                )

            # Quy tắc: Lớp vẽ bắt buộc ở phòng G313
            if ("VẼ" in content_check or "DRAWING" in content_check) and room != "G313":
                violations.append(
                    Violation(
                        rule_id="DRAWING_ROOM_VIOLATION",
                        description=f"Môn/Lớp vẽ phải được xếp ở phòng G313, hiện tại ở {room}.",
                        severity="HARD",
                    )
                )

        # Tối đa 2 tiết liên tiếp trong một ngày cho giáo viên và lớp
        for teacher, days_map in teacher_day_periods.items():
            violations += _check_max_consecutive("Giáo viên", teacher, days_map, max_run)
        for class_group, days_map in class_day_periods.items():
            violations += _check_max_consecutive("Lớp", class_group, days_map, max_run)

        return violations

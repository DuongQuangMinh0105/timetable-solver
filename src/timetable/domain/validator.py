from dataclasses import dataclass
from typing import Any


@dataclass
class Violation:
    """Mô tả một lỗi vi phạm quy tắc thời khóa biểu."""

    rule_id: str
    description: str
    severity: str = "HARD"  # "HARD" hoặc "SOFT"


class Validator:
    """Bộ kiểm tra tính hợp lệ của thời khóa biểu dựa trên các domain entities và rules."""

    def validate(self, timetable: list[dict[str, Any]]) -> list[Violation]:
        """Thực hiện validate thời khóa biểu và trả về danh sách các vi phạm (nếu có)."""
        violations: list[Violation] = []

        # Kiểm tra thời khóa biểu trống
        if not timetable:
            violations.append(
                Violation(
                    rule_id="TIMETABLE_EMPTY",
                    description="Thời khóa biểu không được để trống.",
                    severity="HARD",
                )
            )
            return violations

        # Theo dõi các resource đã sử dụng theo từng tiết học để phát hiện trùng lặp
        used_slots: dict[int, dict[str, set[str]]] = {}

        for entry in timetable:
            period_val = entry.get("period", 0)
            period = int(period_val) if isinstance(period_val, int) else 0
            
            room_val = entry.get("room")
            teacher_val = entry.get("teacher")
            class_group_val = entry.get("class_group")

            room = str(room_val) if room_val is not None else ""
            teacher = str(teacher_val) if teacher_val is not None else ""
            class_group = str(class_group_val) if class_group_val is not None else ""

            # 1. Kiểm tra tiết học nằm trong khoảng 1-6
            if not (1 <= period <= 6):
                violations.append(
                    Violation(
                        rule_id="INVALID_PERIOD",
                        description=f"Tiết học {period} không hợp lệ (phải từ 1 đến 6).",
                        severity="HARD",
                    )
                )

            if period not in used_slots:
                used_slots[period] = {"rooms": set(), "teachers": set(), "classes": set()}

            # 2. Kiểm tra trùng phòng
            if room:
                if room in used_slots[period]["rooms"]:
                    violations.append(
                        Violation(
                            rule_id="ROOM_CONFLICT",
                            description=f"Phòng {room} bị trùng lịch ở tiết {period}.",
                            severity="HARD",
                        )
                    )
                else:
                    used_slots[period]["rooms"].add(room)

            # 3. Kiểm tra trùng giáo viên
            if teacher:
                if teacher in used_slots[period]["teachers"]:
                    violations.append(
                        Violation(
                            rule_id="TEACHER_CONFLICT",
                            description=f"Giáo viên {teacher} bị trùng lịch ở tiết {period}.",
                            severity="HARD",
                        )
                    )
                else:
                    used_slots[period]["teachers"].add(teacher)

            # 4. Kiểm tra trùng lớp
            if class_group:
                if class_group in used_slots[period]["classes"]:
                    violations.append(
                        Violation(
                            rule_id="CLASS_CONFLICT",
                            description=f"Lớp {class_group} bị trùng lịch ở tiết {period}.",
                            severity="HARD",
                        )
                    )
                else:
                    used_slots[period]["classes"].add(class_group)

        return violations
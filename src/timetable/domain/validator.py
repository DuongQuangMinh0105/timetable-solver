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

    def validate(self, timetable: Any, rules: list[Any]) -> list[Violation]:
        """Thực hiện validate thời khóa biểu và trả về danh sách các vi phạm (nếu có)."""
        violations: list[Violation] = []
        
        # Khung logic kiểm tra cơ bản (có thể mở rộng theo rule cụ thể)
        if not timetable:
            violations.append(
                Violation(
                    rule_id="TIMETABLE_EMPTY",
                    description="Thời khóa biểu không được để trống.",
                    severity="HARD",
                )
            )

        return violations
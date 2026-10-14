from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Violation:
    """Mô tả một lỗi vi phạm quy tắc thời khóa biểu."""

    rule_id: str
    description: str
    severity: str = "HARD"  # "HARD" hoặc "SOFT"

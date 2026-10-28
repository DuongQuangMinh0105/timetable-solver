"""Sửa kết quả: chuyển lịch giải thành bảng sửa được và ngược lại (không phụ thuộc streamlit)."""

from typing import Any

Rows = list[dict[str, Any]]

LOCKED = "locked"
READ_ONLY = ("unit_id", "course_id", "class_id", "teacher_id", "duration")
API_FIELDS = ("unit_id", "day", "start_period", "room_id")


def to_edit_rows(assignments: Rows) -> Rows:
    """Mỗi phân công thành một dòng sửa được, kèm cột `locked` (khóa ca khi giải lại)."""
    return [{**a, LOCKED: False} for a in assignments]


def _int(value: Any) -> int | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() and number >= 0 else None


def to_api_rows(rows: Rows) -> tuple[Rows, list[str]]:
    """Dòng đã sửa thành dòng gửi API (unit_id, day, start_period, room_id); trả kèm lỗi nhập."""
    errors: list[str] = []
    result: Rows = []
    seen: set[str] = set()
    for number, row in enumerate(rows, start=1):
        unit_id = str(row.get("unit_id") or "").strip()
        day, period = _int(row.get("day")), _int(row.get("start_period"))
        room = str(row.get("room_id") or "").strip()
        if not unit_id or day is None or period is None or not room:
            errors.append(f"Dòng {number} ({unit_id or '?'}): cần ngày, tiết (số >= 0) và phòng.")
            continue
        if unit_id in seen:
            errors.append(f"Dòng {number}: ca học {unit_id} xuất hiện hai lần.")
        seen.add(unit_id)
        result.append({"unit_id": unit_id, "day": day, "start_period": period, "room_id": room})
    return result, errors


def changed_units(original: Rows, edited: Rows) -> list[str]:
    """Các ca có ngày, tiết hoặc phòng khác bản gốc."""
    before = {r["unit_id"]: tuple(r[f] for f in API_FIELDS[1:]) for r in original}
    return [
        r["unit_id"]
        for r in edited
        if r["unit_id"] in before and tuple(r[f] for f in API_FIELDS[1:]) != before[r["unit_id"]]
    ]


def fixed_assignments(rows: Rows, original: Rows) -> Rows:
    """Các ca giữ nguyên khi giải lại: ca đánh dấu `locked` và ca đã bị sửa so với bản gốc."""
    api_rows, _ = to_api_rows(rows)
    locked = {str(r["unit_id"]) for r in rows if r.get(LOCKED)}
    keep = locked | set(changed_units(original, api_rows))
    return [r for r in api_rows if r["unit_id"] in keep]

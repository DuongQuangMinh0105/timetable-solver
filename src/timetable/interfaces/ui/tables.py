"""Chuyển dữ liệu bài toán (JSON `solve`) sang các bảng để người dùng sửa và ngược lại.

Không phụ thuộc streamlit nên kiểm thử được. Mỗi bảng là danh sách dòng (dict). Ngày và tiết hiển
thị theo số thứ tự từ 1 cho dễ đọc; JSON dùng chỉ số từ 0.
"""

import math
from typing import Any

from pydantic import ValidationError

from timetable.application.dto.solve_request import SolveRequest
from timetable.infrastructure.problem_loader import InvalidProblemError, problem_from_dict

Rows = list[dict[str, Any]]

ROOM_COLUMNS = ("id", "name", "capacity", "room_type", "also_supports")
TEACHER_COLUMNS = ("id", "name", "department")
CLASS_COLUMNS = ("id", "name", "size", "kind")
COURSE_COLUMNS = (
    "id",
    "name",
    "class_id",
    "teacher_id",
    "periods_per_week",
    "required_room_type",
    "department",
)
TABLE_NAMES = ("rooms", "teachers", "classes", "courses")


def clean(value: Any) -> Any:
    """Đưa ô trống (None, NaN, chuỗi rỗng) về None và số nguyên dạng float về int."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def payload_to_tables(payload: dict[str, Any]) -> dict[str, Any]:
    """Tách payload thành bảng phòng, giáo viên, lớp, môn và thông số lưới."""
    grid = payload["grid"]
    return {
        "rooms": [
            {
                **{c: r.get(c) for c in ROOM_COLUMNS},
                "also_supports": ", ".join(r.get("also_supports", [])),
            }
            for r in payload["rooms"]
        ],
        "teachers": [{c: t.get(c) for c in TEACHER_COLUMNS} for t in payload["teachers"]],
        "classes": [{c: g.get(c) for c in CLASS_COLUMNS} for g in payload["class_groups"]],
        "courses": [{c: c_.get(c) for c in COURSE_COLUMNS} for c_ in payload["courses"]],
        "grid": {
            "days": grid["days"],
            "periods": grid["periods"],
            "allowed_periods": ", ".join(str(p + 1) for p in grid["allowed_periods"]),
        },
    }


def _department(row: dict[str, Any]) -> dict[str, str]:
    """Cột nhóm chuyên môn là tùy chọn: trống thì bỏ hẳn khóa khỏi payload."""
    value = row.get("department")
    return {} if value is None else {"department": str(value)}


def _rows(table: Rows, columns: tuple[str, ...]) -> Rows:
    rows = [{c: clean(r.get(c)) for c in columns} for r in table]
    return [r for r in rows if any(v is not None for v in r.values())]


def _required(name: str, rows: Rows, columns: tuple[str, ...], errors: list[str]) -> None:
    seen: set[str] = set()
    for number, row in enumerate(rows, start=1):
        missing = [c for c in columns if row.get(c) is None]
        if missing:
            errors.append(f"Bảng {name}, dòng {number}: thiếu {', '.join(missing)}.")
        key = row.get("id")
        if key is not None:
            if str(key) in seen:
                errors.append(f"Bảng {name}, dòng {number}: trùng id '{key}'.")
            seen.add(str(key))


def _positive(name: str, rows: Rows, column: str, errors: list[str]) -> None:
    for number, row in enumerate(rows, start=1):
        value = row.get(column)
        if value is not None and not (isinstance(value, int) and value >= 1):
            errors.append(f"Bảng {name}, dòng {number}: {column} phải là số nguyên >= 1.")


def _parse_periods(text: Any, periods: int, errors: list[str]) -> list[int]:
    try:
        values = sorted({int(p) for p in str(text).replace(";", ",").split(",") if p.strip()})
    except ValueError:
        errors.append("Lưới: các tiết cho phép phải là số, cách nhau bởi dấu phẩy (ví dụ 1, 2, 3).")
        return [0]
    if not values or values[0] < 1 or values[-1] > periods:
        errors.append(f"Lưới: các tiết cho phép phải nằm trong 1 đến {periods}.")
        return [0]
    return [v - 1 for v in values]


def tables_to_payload(
    tables: dict[str, Any],
    base: dict[str, Any],
    fixed_assignments: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Ghép các bảng đã sửa thành payload `solve`. Trả (payload, lỗi), có lỗi thì payload=None.

    `base` cho các phần không sửa được (schema_version, constraints, soft_weights, solver...).
    """
    errors: list[str] = []
    rooms = _rows(tables["rooms"], ROOM_COLUMNS)
    teachers = _rows(tables["teachers"], TEACHER_COLUMNS)
    classes = _rows(tables["classes"], CLASS_COLUMNS)
    courses = _rows(tables["courses"], COURSE_COLUMNS)
    for name, rows, columns in (
        ("Phòng", rooms, ("id", "name", "capacity")),
        ("Giáo viên", teachers, ("id", "name")),
        ("Lớp", classes, ("id", "name", "size")),
        ("Môn", courses, ("id", "name", "class_id", "teacher_id", "periods_per_week")),
    ):
        if not rows:
            errors.append(f"Bảng {name} đang trống.")
        _required(name, rows, columns, errors)
    _positive("Phòng", rooms, "capacity", errors)
    _positive("Lớp", classes, "size", errors)
    _positive("Môn", courses, "periods_per_week", errors)

    class_ids = {str(r["id"]) for r in classes if r["id"] is not None}
    teacher_ids = {str(r["id"]) for r in teachers if r["id"] is not None}
    for number, row in enumerate(courses, start=1):
        if row["class_id"] is not None and str(row["class_id"]) not in class_ids:
            errors.append(
                f"Bảng Môn, dòng {number}: lớp '{row['class_id']}' không có trong bảng Lớp."
            )
        if row["teacher_id"] is not None and str(row["teacher_id"]) not in teacher_ids:
            errors.append(
                f"Bảng Môn, dòng {number}: giáo viên '{row['teacher_id']}' "
                "không có trong bảng Giáo viên."
            )

    grid = tables["grid"]
    days, periods = clean(grid.get("days")), clean(grid.get("periods"))
    if not (isinstance(days, int) and days >= 1 and isinstance(periods, int) and periods >= 1):
        errors.append("Lưới: số ngày và số tiết phải là số nguyên >= 1.")
        days, periods = 1, 1
    allowed = _parse_periods(grid.get("allowed_periods"), periods, errors)
    if errors:
        return None, errors

    payload = {k: v for k, v in base.items() if k not in ("lesson_units", "fixed_assignments")}
    payload.update(
        {
            "grid": {"days": days, "periods": periods, "allowed_periods": allowed},
            "rooms": [
                {
                    "id": str(r["id"]),
                    "name": str(r["name"]),
                    "capacity": r["capacity"],
                    "room_type": str(r["room_type"] or "standard"),
                    "also_supports": [
                        s.strip() for s in str(r["also_supports"] or "").split(",") if s.strip()
                    ],
                }
                for r in rooms
            ],
            "teachers": [
                {"id": str(r["id"]), "name": str(r["name"]), **_department(r)} for r in teachers
            ],
            "class_groups": [
                {
                    "id": str(r["id"]),
                    "name": str(r["name"]),
                    "size": r["size"],
                    "kind": str(r["kind"] or "regular"),
                }
                for r in classes
            ],
            "courses": [
                {
                    "id": str(r["id"]),
                    "name": str(r["name"]),
                    "class_id": str(r["class_id"]),
                    "teacher_id": str(r["teacher_id"]),
                    "periods_per_week": r["periods_per_week"],
                    "required_room_type": str(r["required_room_type"] or "standard"),
                    **_department(r),
                }
                for r in courses
            ],
        }
    )
    if fixed_assignments:
        payload["fixed_assignments"] = fixed_assignments
    try:
        SolveRequest.model_validate(payload)
        problem_from_dict(payload)
    except ValidationError as exc:
        return None, [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
    except (InvalidProblemError, ValueError, KeyError) as exc:
        return None, [str(exc)]
    return payload, []

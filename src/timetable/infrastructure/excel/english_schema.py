"""Đọc file Excel theo mẫu tiếng Anh của P5 (sheet Teachers, Rooms, Classes, Courses, Periods).

Mẫu này khác mẫu tiếng Việt của `OpenpyxlExcelImporter` (sheet Phòng, Giáo viên, Lớp, Môn). Hàm
`convert` chuyển nó về cùng dạng dữ liệu `solve` để dùng chung bộ giải.

Các cột `unavailable_slots` (giáo viên) và `fixed_day`, `fixed_period` (môn) hiện CHƯA đưa vào mô
hình: bộ giải bỏ qua chúng. Hàm chỉ kiểm tra giá trị nằm trong lưới tiết và trả về cảnh báo để
người dùng biết.
"""

from typing import Any

from timetable.application.ports.excel_importer import ExcelImportError
from timetable.infrastructure.generator import MAX_CONSECUTIVE_PERIODS, SCHEMA_VERSION

ENGLISH_SHEETS = ("Teachers", "Rooms", "Classes", "Courses", "Periods")
SPECIAL_ROOM_TYPE = "mba"  # phòng đặc biệt (is_special=1) và môn requires_special_room=1


def is_english_workbook(sheetnames: list[str]) -> bool:
    return all(name in sheetnames for name in ENGLISH_SHEETS)


def _rows(
    wb: Any, sheet: str, required: tuple[str, ...], errors: list[str]
) -> list[dict[str, Any]]:
    iterator = wb[sheet].iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in (next(iterator, None) or ())]
    missing = [c for c in required if c not in header]
    if missing:
        errors.append(f"Sheet {sheet}, dòng 1: thiếu cột {', '.join(missing)}.")
        return []
    rows = []
    for number, values in enumerate(iterator, start=2):
        record = dict(zip(header, values, strict=False))
        if all(v is None or (isinstance(v, str) and not v.strip()) for v in record.values()):
            continue
        empty = [c for c in required if record.get(c) in (None, "")]
        if empty:
            errors.append(f"Sheet {sheet}, dòng {number}: thiếu giá trị {', '.join(empty)}.")
            continue
        record["_row"] = number
        rows.append(record)
    return rows


def _positive_int(value: Any, where: str, errors: list[str]) -> int:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int) and not isinstance(value, bool) and value >= 1:
        return value
    errors.append(f"{where}: phải là số nguyên >= 1, nhận được {value!r}.")
    return 1


def convert(wb: Any) -> tuple[dict[str, Any], list[str]]:
    """Trả về (dữ liệu solve, cảnh báo). Ném `ExcelImportError` nếu dữ liệu sai."""
    errors: list[str] = []
    warnings: list[str] = []
    teachers = _rows(wb, "Teachers", ("teacher_id", "name"), errors)
    rooms = _rows(wb, "Rooms", ("room_id", "name", "capacity"), errors)
    classes = _rows(wb, "Classes", ("class_id", "name", "size"), errors)
    courses = _rows(
        wb, "Courses", ("course_id", "class_id", "teacher_id", "sessions_per_week"), errors
    )
    periods = _rows(wb, "Periods", ("day", "period"), errors)

    days = sorted({int(p["day"]) for p in periods if isinstance(p["day"], int | float)})
    slots = sorted({int(p["period"]) for p in periods if isinstance(p["period"], int | float)})
    if not days or not slots:
        errors.append("Sheet Periods: không có ngày hoặc tiết nào.")
        days, slots = [1], [1]
    last_day, last_period = max(days), max(slots)

    teacher_ids = {str(t["teacher_id"]) for t in teachers}
    class_ids = {str(c["class_id"]) for c in classes}
    class_data = [
        {
            "id": str(c["class_id"]),
            "name": str(c["name"]),
            "size": _positive_int(c["size"], f"Sheet Classes, dòng {c['_row']}, cột size", errors),
            "kind": "mba" if str(c.get("program") or "").strip().upper() == "MBA" else "regular",
        }
        for c in classes
    ]
    room_data = [
        {
            "id": str(r["room_id"]),
            "name": str(r["name"]),
            "capacity": _positive_int(
                r["capacity"], f"Sheet Rooms, dòng {r['_row']}, cột capacity", errors
            ),
            "room_type": SPECIAL_ROOM_TYPE
            if str(r.get("is_special") or "0") in ("1", "True")
            else "standard",
            "also_supports": [],
        }
        for r in rooms
    ]

    course_data = []
    for c in courses:
        row = c["_row"]
        if str(c["class_id"]) not in class_ids:
            errors.append(f"Sheet Courses, dòng {row}: lớp '{c['class_id']}' không có.")
        if str(c["teacher_id"]) not in teacher_ids:
            errors.append(f"Sheet Courses, dòng {row}: giáo viên '{c['teacher_id']}' không có.")
        fixed_day, fixed_period = c.get("fixed_day"), c.get("fixed_period")
        if fixed_day is not None and fixed_day not in days:
            errors.append(
                f"Sheet Courses, dòng {row}: môn {c['course_id']} ép vào ngày {fixed_day}, "
                f"ngoài các ngày hợp lệ {days[0]}..{last_day}."
            )
        if fixed_period is not None and fixed_period not in slots:
            errors.append(
                f"Sheet Courses, dòng {row}: môn {c['course_id']} ép vào tiết {fixed_period}, "
                f"ngoài khoảng tiết hợp lệ {slots[0]}..{last_period}."
            )
        if fixed_day is not None or fixed_period is not None:
            warnings.append(
                f"Môn {c['course_id']}: fixed_day/fixed_period chưa được áp dụng vào mô hình."
            )
        requires_special = str(c.get("requires_special_room") or "0") in ("1", "True")
        course_data.append(
            {
                "id": str(c["course_id"]),
                "name": str(c["course_id"]),
                "class_id": str(c["class_id"]),
                "teacher_id": str(c["teacher_id"]),
                "periods_per_week": _positive_int(
                    c["sessions_per_week"],
                    f"Sheet Courses, dòng {row}, cột sessions_per_week",
                    errors,
                ),
                "required_room_type": SPECIAL_ROOM_TYPE if requires_special else "standard",
            }
        )
    if any(t.get("unavailable_slots") for t in teachers):
        warnings.append("Cột unavailable_slots của giáo viên chưa được áp dụng vào mô hình.")

    if errors:
        raise ExcelImportError("\n".join(errors))

    data = {
        "schema_version": SCHEMA_VERSION,
        "grid": {
            "days": last_day,
            "periods": last_period,
            "allowed_periods": [p - 1 for p in slots],
        },
        "rooms": room_data,
        "teachers": [{"id": str(t["teacher_id"]), "name": str(t["name"])} for t in teachers],
        "class_groups": class_data,
        "courses": course_data,
        "constraints": {"max_consecutive_periods": MAX_CONSECUTIVE_PERIODS},
    }
    return data, warnings

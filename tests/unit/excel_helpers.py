from pathlib import Path
from typing import Any

from openpyxl import Workbook

Sheets = dict[str, list[list[Any]]]


def sheets_from_data(data: dict[str, Any]) -> Sheets:
    """Chuyển dữ liệu của generator thành nội dung các sheet (dòng đầu là tiêu đề)."""
    return {
        "Phòng": [["id", "name", "capacity", "room_type", "also_supports"]]
        + [
            [r["id"], r["name"], r["capacity"], r["room_type"], ",".join(r["also_supports"])]
            for r in data["rooms"]
        ],
        "Giáo viên": [["id", "name"]] + [[t["id"], t["name"]] for t in data["teachers"]],
        "Lớp": [["id", "name", "size", "kind"]]
        + [[c["id"], c["name"], c["size"], c["kind"]] for c in data["class_groups"]],
        "Môn": [["id", "name", "class_id", "teacher_id", "periods_per_week", "required_room_type"]]
        + [
            [
                c["id"],
                c["name"],
                c["class_id"],
                c["teacher_id"],
                c["periods_per_week"],
                c["required_room_type"],
            ]
            for c in data["courses"]
        ],
    }


def write_workbook(path: Path, sheets: Sheets) -> Path:
    wb = Workbook()
    wb.remove(wb.active)  # type: ignore[arg-type]
    for title, rows in sheets.items():
        ws = wb.create_sheet(title)
        for row in rows:
            ws.append(row)
    wb.save(path)
    return path

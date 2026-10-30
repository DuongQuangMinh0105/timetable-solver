"""Hiển thị lịch cho người dùng: tên thứ, tiết, giờ học và lưới tuần (không phụ thuộc streamlit)."""

from typing import Any

from timetable.domain.entities.time_grid import DEFAULT_PERIOD_TIMES
from timetable.domain.services.time_labels import DAY_NAMES, day_name

Rows = list[dict[str, Any]]

PERIOD_PREFIX = "Tiết "


def period_label(period: int) -> str:
    """Chỉ số tiết (từ 0) thành nhãn "Tiết 1"."""
    return f"{PERIOD_PREFIX}{period + 1}"


def day_options(days: int) -> list[str]:
    return [day_name(d) for d in range(days)]


def period_options(periods: list[int]) -> list[str]:
    return [period_label(p) for p in periods]


def parse_day(value: Any) -> int | None:
    """Nhãn "Thứ Ba" hoặc số (từ 0) thành chỉ số ngày; không hiểu thì None."""
    if isinstance(value, str):
        text = value.strip()
        if text in DAY_NAMES:
            return DAY_NAMES.index(text)
    return _index(value)


def parse_period(value: Any) -> int | None:
    """Nhãn "Tiết 3" (đánh số từ 1) hoặc số (từ 0) thành chỉ số tiết; không hiểu thì None."""
    if isinstance(value, str) and value.strip().startswith(PERIOD_PREFIX):
        number = _index(value.strip()[len(PERIOD_PREFIX) :])
        return None if number is None or number < 1 else number - 1
    return _index(value)


def _index(value: Any) -> int | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() and number >= 0 else None


def time_range(start: int, duration: int, times: tuple[tuple[str, str], ...]) -> str:
    """Giờ học của ca bắt đầu ở `start`, kéo dài `duration` tiết; rỗng nếu không biết giờ."""
    end = start + duration - 1
    if not times or end >= len(times):
        return ""
    return f"{times[start][0]}–{times[end][1]}"


def periods_text(start: int, duration: int) -> str:
    first = start + 1
    return f"Tiết {first}" if duration <= 1 else f"Tiết {first}–{first + duration - 1}"


def display_rows(
    assignments: Rows,
    course_names: dict[str, str] | None = None,
    times: tuple[tuple[str, str], ...] = DEFAULT_PERIOD_TIMES,
) -> Rows:
    """Phân công thành các dòng tiếng Việt, sắp theo thứ rồi tiết."""
    names = course_names or {}
    ordered = sorted(assignments, key=lambda a: (a["day"], a["start_period"], a["unit_id"]))
    rows: Rows = []
    for a in ordered:
        duration = int(a.get("duration") or 1)
        rows.append(
            {
                "Thứ": day_name(a["day"]),
                "Tiết": periods_text(a["start_period"], duration),
                "Giờ": time_range(a["start_period"], duration, times),
                "Môn": names.get(str(a["course_id"]), a["course_id"]),
                "Lớp": a["class_id"],
                "Giáo viên": a["teacher_id"],
                "Phòng": a["room_id"],
                "Mã ca": a["unit_id"],
            }
        )
    return rows


def weekly_grid(
    assignments: Rows,
    cell: tuple[str, ...],
    days: int,
    periods: list[int],
    course_names: dict[str, str] | None = None,
) -> Rows:
    """Lưới tuần: mỗi dòng một tiết, mỗi cột một thứ; ô ghi các trường trong `cell`.

    `cell` là tên các khóa của phân công cần ghi vào ô (ví dụ ("course_id", "room_id")); mã môn
    được đổi sang tên môn nếu biết. Ca 2 tiết chiếm cả hai dòng.
    """
    names = course_names or {}
    texts: dict[tuple[int, int], list[str]] = {}
    for a in assignments:
        parts = [str(names.get(str(a[k]), a[k])) if k == "course_id" else str(a[k]) for k in cell]
        for offset in range(int(a.get("duration") or 1)):
            texts.setdefault((a["day"], a["start_period"] + offset), []).append(" · ".join(parts))
    return [
        {
            "": period_label(p),
            **{day_name(d): " / ".join(texts.get((d, p), [])) for d in range(days)},
        }
        for p in periods
    ]

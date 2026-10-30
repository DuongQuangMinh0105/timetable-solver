from timetable.domain.services.time_labels import day_name, period_name, slot_name
from timetable.interfaces.ui.result_edit import to_api_rows, to_edit_rows
from timetable.interfaces.ui.schedule_view import (
    day_options,
    display_rows,
    parse_day,
    parse_period,
    period_options,
    weekly_grid,
)

ROWS = [
    {"unit_id": "u1", "course_id": "C1", "class_id": "A", "teacher_id": "GV1",
     "day": 0, "start_period": 0, "duration": 2, "room_id": "R1"},
    {"unit_id": "u2", "course_id": "C2", "class_id": "A", "teacher_id": "GV2",
     "day": 5, "start_period": 3, "duration": 1, "room_id": "R2"},
]  # fmt: skip


def test_day_and_slot_names() -> None:
    assert [day_name(d) for d in range(6)] == [
        "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"
    ]  # fmt: skip
    assert period_name(0) == "tiết 1"
    assert slot_name(1, 2) == "Thứ Ba, tiết 3"


def test_parse_accepts_labels_and_plain_numbers() -> None:
    assert parse_day("Thứ Tư") == 2 and parse_day(2) == 2 and parse_day("2") == 2
    assert parse_period("Tiết 1") == 0 and parse_period("Tiết 6") == 5 and parse_period(4) == 4
    assert parse_day("Thứ Xyz") is None and parse_period("Tiết 0") is None
    assert parse_day(-1) is None


def test_options_are_vietnamese() -> None:
    assert day_options(6)[:3] == ["Thứ Hai", "Thứ Ba", "Thứ Tư"]
    assert period_options([0, 1]) == ["Tiết 1", "Tiết 2"]


def test_display_rows_use_day_names_periods_and_times() -> None:
    rows = display_rows(ROWS, {"C1": "Lập trình"})
    assert rows[0]["Thứ"] == "Thứ Hai" and rows[0]["Tiết"] == "Tiết 1–2"
    assert rows[0]["Giờ"] == "07:30–10:40" and rows[0]["Môn"] == "Lập trình"
    assert rows[1]["Thứ"] == "Thứ Bảy" and rows[1]["Tiết"] == "Tiết 4"
    assert rows[1]["Môn"] == "C2"  # chưa biết tên môn thì giữ mã


def test_weekly_grid_fills_two_period_blocks() -> None:
    grid = weekly_grid(ROWS, ("course_id", "room_id"), 6, list(range(6)), {"C1": "Lập trình"})
    assert grid[0]["Thứ Hai"] == "Lập trình · R1" and grid[1]["Thứ Hai"] == "Lập trình · R1"
    assert grid[3]["Thứ Bảy"] == "C2 · R2" and grid[2]["Thứ Hai"] == ""
    assert grid[0][""] == "Tiết 1" and "Thứ Bảy" in grid[0]


def test_edit_rows_round_trip_through_labels() -> None:
    edit = to_edit_rows(ROWS)
    assert edit[1]["day"] == "Thứ Bảy" and edit[1]["start_period"] == "Tiết 4"
    api, errors = to_api_rows(edit)
    assert errors == []
    assert api[1] == {"unit_id": "u2", "day": 5, "start_period": 3, "room_id": "R2"}

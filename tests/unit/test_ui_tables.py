from pathlib import Path
from typing import Any

import pytest

from timetable.infrastructure.excel.importer import OpenpyxlExcelImporter
from timetable.interfaces.ui.tables import clean, payload_to_tables, tables_to_payload

SAMPLES = Path(__file__).resolve().parents[2] / "docs" / "samples"


@pytest.fixture
def payload() -> dict[str, Any]:
    return OpenpyxlExcelImporter().load_data(SAMPLES / "ok_basic.xlsx")


def test_round_trip_keeps_the_problem(payload: dict[str, Any]) -> None:
    result, errors = tables_to_payload(payload_to_tables(payload), payload)
    assert errors == []
    assert result is not None
    for key in ("rooms", "teachers", "class_groups", "courses", "grid"):
        assert result[key] == payload[key]


def test_edit_a_course_is_reflected(payload: dict[str, Any]) -> None:
    tables = payload_to_tables(payload)
    tables["courses"][0]["periods_per_week"] = 1
    result, errors = tables_to_payload(tables, payload)
    assert errors == [] and result is not None
    assert result["courses"][0]["periods_per_week"] == 1


def test_nan_and_blank_cells_are_treated_as_empty() -> None:
    assert clean(float("nan")) is None
    assert clean("  ") is None
    assert clean(3.0) == 3


def test_blank_rows_added_by_the_editor_are_ignored(payload: dict[str, Any]) -> None:
    tables = payload_to_tables(payload)
    tables["teachers"].append({"id": None, "name": float("nan")})
    result, errors = tables_to_payload(tables, payload)
    assert errors == [] and result is not None
    assert len(result["teachers"]) == len(payload["teachers"])


def test_errors_are_reported_in_vietnamese(payload: dict[str, Any]) -> None:
    tables = payload_to_tables(payload)
    tables["courses"][0]["teacher_id"] = "KHONG_CO"
    tables["rooms"].append(dict(tables["rooms"][0]))  # trùng id
    tables["classes"][0]["size"] = 0
    result, errors = tables_to_payload(tables, payload)
    assert result is None
    text = "\n".join(errors)
    assert "không có trong bảng Giáo viên" in text
    assert "trùng id" in text
    assert "size phải là số nguyên >= 1" in text


def test_empty_table_is_an_error(payload: dict[str, Any]) -> None:
    tables = payload_to_tables(payload)
    tables["rooms"] = []
    result, errors = tables_to_payload(tables, payload)
    assert result is None and any("Phòng đang trống" in e for e in errors)


def test_bad_grid_is_reported(payload: dict[str, Any]) -> None:
    tables = payload_to_tables(payload)
    tables["grid"]["allowed_periods"] = "1, 99"
    result, errors = tables_to_payload(tables, payload)
    assert result is None and any("Lưới" in e for e in errors)


def test_fixed_assignments_are_attached(payload: dict[str, Any]) -> None:
    fixed = [{"unit_id": "x", "day": 0, "start_period": 0, "room_id": "R101"}]
    result, errors = tables_to_payload(payload_to_tables(payload), payload, fixed)
    # unit_id không tồn tại nên loader từ chối, và lỗi được báo thay vì ném ngoại lệ
    assert result is None and errors

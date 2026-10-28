from timetable.interfaces.ui.result_edit import (
    changed_units,
    fixed_assignments,
    to_api_rows,
    to_edit_rows,
)

ORIGINAL = [
    {"unit_id": "u1", "course_id": "C1", "class_id": "A", "teacher_id": "T1",
     "day": 0, "start_period": 0, "duration": 2, "room_id": "R1"},
    {"unit_id": "u2", "course_id": "C2", "class_id": "B", "teacher_id": "T2",
     "day": 1, "start_period": 2, "duration": 1, "room_id": "R2"},
]  # fmt: skip


def test_edit_rows_start_unlocked() -> None:
    assert all(r["locked"] is False for r in to_edit_rows(ORIGINAL))


def test_api_rows_coerce_numbers_from_the_editor() -> None:
    rows = [{**ORIGINAL[0], "day": 2.0, "start_period": "3"}]
    api, errors = to_api_rows(rows)
    assert errors == []
    assert api == [{"unit_id": "u1", "day": 2, "start_period": 3, "room_id": "R1"}]


def test_invalid_cells_are_reported() -> None:
    rows = [{**ORIGINAL[0], "day": -1}, {**ORIGINAL[1], "room_id": ""}]
    api, errors = to_api_rows(rows)
    assert api == [] and len(errors) == 2


def test_duplicate_unit_is_reported() -> None:
    _, errors = to_api_rows([ORIGINAL[0], ORIGINAL[0]])
    assert any("hai lần" in e for e in errors)


def test_changed_units_compare_with_original() -> None:
    edited, _ = to_api_rows([{**ORIGINAL[0], "room_id": "R9"}, ORIGINAL[1]])
    assert changed_units(ORIGINAL, edited) == ["u1"]


def test_fixed_assignments_keep_locked_and_changed_units() -> None:
    rows = to_edit_rows(ORIGINAL)
    rows[0]["start_period"] = 4  # đã sửa
    rows[1]["locked"] = True  # đã khóa
    keep = fixed_assignments(rows, ORIGINAL)
    assert {r["unit_id"] for r in keep} == {"u1", "u2"}
    assert next(r for r in keep if r["unit_id"] == "u1")["start_period"] == 4


def test_untouched_unlocked_units_are_not_fixed() -> None:
    assert fixed_assignments(to_edit_rows(ORIGINAL), ORIGINAL) == []

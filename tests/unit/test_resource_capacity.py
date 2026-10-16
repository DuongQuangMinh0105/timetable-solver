from dataclasses import replace

from solver_helpers import make_problem, unit
from timetable.domain.entities import Room, TimeGrid
from timetable.domain.services.resource_capacity import (
    resource_capacity_issues,
    room_capacity_issues,
    teacher_capacity_issues,
    weekly_cells,
)

GRID = TimeGrid(days=1, periods=8, allowed_periods=(0, 1))  # 2 tiết mỗi tuần cho mỗi tài nguyên


def test_weekly_cells() -> None:
    assert weekly_cells(make_problem([unit("a", "C", "T")], grid=GRID)) == 2


def test_teacher_over_capacity_is_reported() -> None:
    units = [unit(f"u{i}", f"C{i}", "T") for i in range(3)]  # 3 tiết, giáo viên chỉ có 2
    issues = teacher_capacity_issues(make_problem(units, grid=GRID))
    assert [i.code for i in issues] == ["teacher_capacity"]
    assert "T" in issues[0].message


def test_teacher_at_capacity_is_fine() -> None:
    units = [unit(f"u{i}", f"C{i}", "T") for i in range(2)]
    assert teacher_capacity_issues(make_problem(units, grid=GRID)) == []


def test_single_room_type_over_capacity_is_reported() -> None:
    rooms = (Room("M", "M", 30, "mba", ("standard",)), Room("S", "S", 30))
    units = [unit(f"m{i}", f"C{i}", f"T{i}", room_type="mba") for i in range(3)]  # 3 tiết, 1 phòng
    issues = room_capacity_issues(make_problem(units, rooms=rooms, grid=GRID))
    assert [i.code for i in issues] == ["room_capacity"]
    assert "M" in issues[0].message


def test_flexible_units_are_not_flagged_when_rooms_suffice() -> None:
    rooms = (Room("M", "M", 30, "mba", ("standard",)), Room("S", "S", 30))
    units = [unit(f"u{i}", f"C{i}", f"T{i}") for i in range(4)]  # 4 tiết, hai phòng x 2 tiết
    assert room_capacity_issues(make_problem(units, rooms=rooms, grid=GRID)) == []


def test_hall_condition_counts_nested_room_sets() -> None:
    rooms = (Room("M", "M", 30, "mba", ("standard",)), Room("S", "S", 30))
    units = [unit(f"m{i}", f"C{i}", f"T{i}", room_type="mba") for i in range(2)]
    units += [unit(f"s{i}", f"D{i}", f"U{i}") for i in range(3)]  # tổng 5 tiết > 2 phòng x 2 tiết
    issues = room_capacity_issues(make_problem(units, rooms=rooms, grid=GRID))
    assert [i.code for i in issues] == ["room_capacity"]


def test_sample_problem_has_no_capacity_issue(sample_problem) -> None:  # type: ignore[no-untyped-def]
    assert resource_capacity_issues(sample_problem) == []
    assert resource_capacity_issues(replace(sample_problem, lesson_units=())) == []

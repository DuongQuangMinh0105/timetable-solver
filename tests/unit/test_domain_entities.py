import pytest

from timetable.domain.entities import (
    Assignment,
    ClassGroup,
    Problem,
    Room,
    Slot,
    TimeGrid,
    Timetable,
)


def test_time_grid_default_is_6_days_8_periods_with_6_usable() -> None:
    grid = TimeGrid()
    assert grid.days == 6
    assert grid.periods == 8
    assert grid.allowed_periods == (0, 1, 2, 3, 4, 5)
    assert grid.num_slots == 36
    assert len(list(grid.slots())) == 36


def test_time_grid_forbids_periods_7_and_8() -> None:
    grid = TimeGrid()
    assert grid.contains(Slot(5, 5))
    assert not grid.contains(Slot(0, 6))
    assert not grid.contains(Slot(0, 7))
    assert not grid.contains(Slot(6, 0))


def test_time_grid_saturday() -> None:
    grid = TimeGrid()
    assert grid.is_saturday(5)
    assert not grid.is_saturday(0)


def test_time_grid_period_times_match_school_schedule() -> None:
    grid = TimeGrid()
    assert grid.period_times[0] == ("07:30", "09:00")
    assert grid.period_times[7] == ("19:30", "21:00")


def test_time_grid_rejects_invalid_config() -> None:
    with pytest.raises(ValueError):
        TimeGrid(days=0)
    with pytest.raises(ValueError):
        TimeGrid(allowed_periods=())
    with pytest.raises(ValueError):
        TimeGrid(allowed_periods=(0, 9))
    with pytest.raises(ValueError):
        TimeGrid(periods=6, allowed_periods=(0, 1))  # period_times mặc định có 8 phần tử


def test_time_grid_custom_without_period_times() -> None:
    grid = TimeGrid(periods=6, allowed_periods=(0, 1, 2, 3, 4, 5), period_times=())
    assert grid.num_slots == 36


def test_room_can_host_by_type() -> None:
    standard = Room(id="G502", name="G502", capacity=30)
    mba = Room(id="G316", name="G316", capacity=30, room_type="mba", also_supports=("standard",))
    art = Room(id="G313", name="G313", capacity=30, room_type="art")

    assert standard.can_host("standard") and not standard.can_host("mba")
    assert mba.can_host("mba") and mba.can_host("standard")
    assert mba.is_primary_for("mba") and not mba.is_primary_for("standard")
    assert art.can_host("art") and not art.can_host("standard")


def test_entities_validate_positive_numbers() -> None:
    with pytest.raises(ValueError):
        Room(id="R1", name="A101", capacity=0)
    with pytest.raises(ValueError):
        ClassGroup(id="C1", name="10A1", size=-1)


def test_timetable_lookup_by_unit() -> None:
    a = Assignment(unit_id="U1", day=0, period=2, room_id="R1")
    timetable = Timetable(assignments=(a,))
    assert timetable.for_unit("U1") == a
    assert timetable.for_unit("U2") is None


def test_problem_defaults() -> None:
    problem = Problem(rooms=(), teachers=(), class_groups=(), courses=(), lesson_units=())
    assert problem.grid == TimeGrid()
    assert problem.max_consecutive_periods == 2

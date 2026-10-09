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


def test_time_grid_default_is_6x6() -> None:
    grid = TimeGrid()
    assert grid.days == 6
    assert grid.periods == 6
    assert grid.num_slots == 36
    assert len(list(grid.slots())) == 36


def test_time_grid_contains_and_saturday() -> None:
    grid = TimeGrid()
    assert grid.contains(Slot(5, 5))
    assert not grid.contains(Slot(6, 0))
    assert grid.is_saturday(5)
    assert not grid.is_saturday(0)


def test_time_grid_rejects_invalid_size() -> None:
    with pytest.raises(ValueError):
        TimeGrid(days=0)


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


def test_problem_defaults_to_standard_grid() -> None:
    problem = Problem(rooms=(), teachers=(), class_groups=(), courses=(), lesson_units=())
    assert problem.grid == TimeGrid()

"""Mỗi quy tắc của Validator có ít nhất một case pass và một case fail."""

from solver_helpers import STANDARD_ROOMS, make_problem, unit
from timetable.domain.entities import LessonUnit, Room, TimeGrid, Timetable
from timetable.domain.entities.timetable import Assignment
from timetable.domain.validator import Validator, Violation

G316 = Room("G316", "G316", 30, "mba", ("standard",))
G313 = Room("G313", "G313", 30, "art")
ROOMS = (*STANDARD_ROOMS, G316, G313)
GRID = TimeGrid()  # 6 ngày, tiết 1 đến 6 được phép


def _timetable(*items: tuple[str, int, int, str]) -> Timetable:
    """Mỗi phần tử là (unit_id, day, period, room_id)."""
    return Timetable(tuple(Assignment(u, d, p, r) for u, d, p, r in items))


def _ids(violations: list[Violation]) -> list[str]:
    return [v.rule_id for v in violations]


def _validate(
    units: list[LessonUnit],
    items: tuple[tuple[str, int, int, str], ...],
    max_consecutive: int = 2,
) -> list[str]:
    problem = make_problem(units, rooms=ROOMS, grid=GRID, max_consecutive=max_consecutive)
    return _ids(Validator().validate(problem, _timetable(*items)))


# --- Lịch rỗng và lịch hợp lệ ------------------------------------------------


def test_empty_timetable_is_reported() -> None:
    problem = make_problem([unit("a", "C1", "T1")], rooms=ROOMS, grid=GRID)
    assert _ids(Validator().validate(problem, Timetable())) == ["TIMETABLE_EMPTY"]


def test_valid_timetable_has_no_violation() -> None:
    units = [unit("a", "C1", "T1"), unit("b", "C2", "T2")]
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 0, 0, "R2"))) == []


def test_unknown_unit_is_reported() -> None:
    assert _validate([unit("a", "C1", "T1")], (("zzz", 0, 0, "R1"),)) == ["UNKNOWN_REFERENCE"]


# --- Trùng phòng / giáo viên / lớp --------------------------------------------


def test_room_conflict_pass_different_rooms() -> None:
    units = [unit("a", "C1", "T1"), unit("b", "C2", "T2")]
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 0, 0, "R2"))) == []


def test_room_conflict_fail_same_room_same_slot() -> None:
    units = [unit("a", "C1", "T1"), unit("b", "C2", "T2")]
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 0, 0, "R1"))) == ["ROOM_CONFLICT"]


def test_teacher_conflict_pass_different_slots() -> None:
    units = [unit("a", "C1", "T1"), unit("b", "C2", "T1")]
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 0, 2, "R2"))) == []


def test_teacher_conflict_fail_same_slot() -> None:
    units = [unit("a", "C1", "T1"), unit("b", "C2", "T1")]
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 0, 0, "R2"))) == ["TEACHER_CONFLICT"]


def test_class_conflict_pass_different_slots() -> None:
    units = [unit("a", "C1", "T1"), unit("b", "C1", "T2")]
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 0, 4, "R2"))) == []


def test_class_conflict_fail_same_slot() -> None:
    units = [unit("a", "C1", "T1"), unit("b", "C1", "T2")]
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 0, 0, "R2"))) == ["CLASS_CONFLICT"]


def test_same_room_and_period_on_different_days_is_not_a_conflict() -> None:
    units = [unit("a", "C1", "T1"), unit("b", "C2", "T2")]
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 1, 0, "R1"))) == []


def test_two_period_block_occupies_its_second_period() -> None:
    units = [unit("a", "C1", "T1", duration=2), unit("b", "C2", "T2")]
    # a chiếm tiết 0 và 1; b ở tiết 1 cùng phòng nên trùng.
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 0, 1, "R1"))) == ["ROOM_CONFLICT"]


# --- Tiết nằm trong 1 đến 6 ---------------------------------------------------


def test_period_pass_block_ending_at_the_last_allowed_period() -> None:
    assert _validate([unit("a", "C1", "T1", duration=2)], (("a", 0, 4, "R1"),)) == []


def test_period_fail_period_outside_the_allowed_range() -> None:
    assert _validate([unit("a", "C1", "T1")], (("a", 0, 6, "R1"),)) == ["INVALID_PERIOD"]


def test_period_fail_block_spilling_past_the_last_allowed_period() -> None:
    assert _validate([unit("a", "C1", "T1", duration=2)], (("a", 0, 5, "R1"),)) == [
        "INVALID_PERIOD"
    ]


def test_period_fail_day_outside_the_week() -> None:
    assert _validate([unit("a", "C1", "T1")], (("a", 6, 0, "R1"),)) == ["INVALID_PERIOD"]


# --- Tối đa 2 tiết liên tiếp --------------------------------------------------


def test_max_consecutive_pass_blocks_with_a_rest() -> None:
    units = [unit("a", "C1", "T1", duration=2), unit("b", "C1", "T2", duration=2)]
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 0, 4, "R1"))) == []


def test_max_consecutive_fail_two_adjacent_blocks() -> None:
    units = [unit("a", "C1", "T1", duration=2), unit("b", "C1", "T2", duration=2)]
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 0, 2, "R1"))) == ["MAX_CONSECUTIVE"]


def test_max_consecutive_fail_block_next_to_a_single_period() -> None:
    units = [unit("a", "C1", "T1", duration=2), unit("b", "C1", "T2")]
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 0, 2, "R1"))) == ["MAX_CONSECUTIVE"]


def test_max_consecutive_follows_the_problem_setting() -> None:
    units = [unit("a", "C1", "T1", duration=2), unit("b", "C1", "T2")]
    items = (("a", 0, 0, "R1"), ("b", 0, 2, "R1"))
    assert _validate(units, items, max_consecutive=3) == []


def test_max_consecutive_is_counted_per_class_and_day() -> None:
    units = [unit("a", "C1", "T1", duration=2), unit("b", "C2", "T2", duration=2)]
    # Hai lớp khác nhau, hoặc cùng lớp khác ngày, đều không cộng dồn.
    assert _validate(units, (("a", 0, 0, "R1"), ("b", 0, 2, "R2"))) == []


# --- MBA ở G316, lớp vẽ ở G313 ------------------------------------------------


def test_mba_pass_unit_in_g316() -> None:
    assert _validate([unit("a", "C1", "T1", "mba")], (("a", 0, 0, "G316"),)) == []


def test_mba_fail_unit_outside_g316() -> None:
    assert _validate([unit("a", "C1", "T1", "mba")], (("a", 0, 0, "R1"),)) == ["MBA_ROOM"]


def test_art_pass_unit_in_g313() -> None:
    assert _validate([unit("a", "C1", "T1", "art")], (("a", 0, 0, "G313"),)) == []


def test_art_fail_unit_outside_g313() -> None:
    assert _validate([unit("a", "C1", "T1", "art")], (("a", 0, 0, "R1"),)) == ["ART_ROOM"]


def test_art_fail_unit_in_the_mba_room() -> None:
    assert _validate([unit("a", "C1", "T1", "art")], (("a", 0, 0, "G316"),)) == ["ART_ROOM"]


# --- Ranh giới cứng / mềm -----------------------------------------------------


def test_regular_unit_in_g316_is_not_a_hard_violation() -> None:
    # Chỉ bị phạt mềm (W_G316), nên validator không báo lỗi cứng.
    assert _validate([unit("a", "C1", "T1")], (("a", 0, 0, "G316"),)) == []


def test_regular_unit_in_the_art_room_is_a_hard_violation() -> None:
    assert _validate([unit("a", "C1", "T1")], (("a", 0, 0, "G313"),)) == ["ROOM_TYPE"]

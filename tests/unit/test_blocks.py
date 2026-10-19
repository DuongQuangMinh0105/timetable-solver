from solver_helpers import check_valid, make_problem, one_day_grid, solve, unit
from timetable.application.dto.solve import SolveStatus
from timetable.domain.entities import Course, LessonUnit, Slot
from timetable.domain.services.slot_policy import allowed_starts
from timetable.domain.services.unit_splitter import (
    lesson_units_for_course,
    split_into_blocks,
)

ALIGNED = (0, 2, 4)
SIX = one_day_grid(1, 2, 3, 4, 5, 6)


def test_split_into_blocks() -> None:
    assert split_into_blocks(1) == [1]
    assert split_into_blocks(2) == [2]
    assert split_into_blocks(3) == [2, 1]
    assert split_into_blocks(5) == [2, 2, 1]


def test_lesson_units_for_course() -> None:
    units = lesson_units_for_course(Course("M", "Toán", "C", "T", 3))

    assert [(lesson.id, lesson.duration) for lesson in units] == [
        ("M-0", 2),
        ("M-1", 1),
    ]


def test_block_starts_are_aligned() -> None:
    problem = make_problem(
        [unit("a", "C", "T", duration=2)],
        grid=SIX,
        block_starts=ALIGNED,
    )

    starts = [
        slot.period
        for slot in allowed_starts(problem, problem.lesson_units[0])
    ]

    assert starts == [0, 2, 4]


def test_block_cannot_start_at_last_allowed_period() -> None:
    problem = make_problem(
        [unit("a", "C", "T", duration=2)],
        grid=SIX,
    )

    assert Slot(0, 5) not in set(
        allowed_starts(problem, problem.lesson_units[0])
    )


def test_two_blocks_same_day_need_a_rest() -> None:
    """Hai block phải có thời gian nghỉ giữa các tiết liên tiếp."""
    units = [
        unit("a", "C", "T1", duration=2),
        unit("b", "C", "T2", duration=2),
    ]
    problem = make_problem(units, grid=SIX, block_starts=ALIGNED)

    result = solve(problem)

    assert result.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
    assert result.timetable is not None

    check_valid(problem, result.timetable)

    assert sorted(
        assignment.period for assignment in result.timetable.assignments
    ) == [0, 4]


def test_three_blocks_one_day_infeasible() -> None:
    units = [
        unit(course_id, "C", f"T{course_id}", duration=2)
        for course_id in "abc"
    ]
    problem = make_problem(units, grid=SIX, block_starts=ALIGNED)

    assert solve(problem).status is SolveStatus.INFEASIBLE


def test_block_overlap_with_single_period_is_forbidden() -> None:
    units = [
        unit("a", "C", "T1", duration=2),
        unit("b", "C", "T2"),
    ]
    problem = make_problem(
        units,
        grid=one_day_grid(1, 2),
        block_starts=ALIGNED,
    )

    assert solve(problem).status is SolveStatus.INFEASIBLE


def test_teacher_blocked_across_occupied_periods() -> None:
    units = [
        unit("a", "C1", "T", duration=2),
        unit("b", "C2", "T", duration=2),
    ]
    problem = make_problem(
        units,
        grid=one_day_grid(1, 2, 3),
        block_starts=ALIGNED,
    )

    assert solve(problem).status is SolveStatus.INFEASIBLE


def test_second_session_same_day_is_allowed() -> None:
    units = [
        _lesson_unit("M", 0, 2),
        _lesson_unit("M", 1, 2),
    ]
    problem = make_problem(units, grid=SIX, block_starts=ALIGNED)

    result = solve(problem)

    assert result.timetable is not None
    check_valid(problem, result.timetable)


def _lesson_unit(course: str, index: int, duration: int) -> LessonUnit:
    return LessonUnit(
        id=f"{course}-{index}",
        course_id=course,
        class_id="C",
        teacher_id="T",
        index=index,
        duration=duration,
    )
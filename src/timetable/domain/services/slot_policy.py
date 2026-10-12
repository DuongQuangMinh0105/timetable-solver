from collections.abc import Iterator

from timetable.domain.entities import LessonUnit, Problem, Slot


def allowed_starts(problem: Problem, unit: LessonUnit) -> Iterator[Slot]:
    """Các ô mà đơn vị học có thể bắt đầu.

    Mọi tiết bị chiếm (từ tiết bắt đầu, `duration` tiết) phải là tiết được phép xếp. Block từ
    2 tiết trở lên còn phải bắt đầu ở một tiết trong `Problem.block_starts` (nếu có cấu hình).
    """
    allowed = set(problem.grid.allowed_periods)
    for slot in problem.grid.slots():
        occupied = range(slot.period, slot.period + unit.duration)
        if not all(q in allowed for q in occupied):
            continue
        if (
            unit.duration >= 2
            and problem.block_starts is not None
            and slot.period not in problem.block_starts
        ):
            continue
        yield slot

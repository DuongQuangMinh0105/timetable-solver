from collections import defaultdict
from collections.abc import Callable

from ortools.sat.python import cp_model

from timetable.infrastructure.solver.encoder import ModelContext, VarKey


def _at_most_one_per_group(
    ctx: ModelContext, group_of: Callable[[VarKey], tuple[str, int, int]]
) -> None:
    groups: dict[tuple[str, int, int], list[cp_model.IntVar]] = defaultdict(list)
    for key, var in ctx.x.items():
        groups[group_of(key)].append(var)
    for variables in groups.values():
        if len(variables) > 1:
            ctx.model.add_at_most_one(variables)


class EachUnitOnceEncoder:
    """Mỗi đơn vị học được xếp vào đúng một ô (ngày, tiết, phòng)."""

    name = "each_unit_once"

    def encode(self, ctx: ModelContext) -> None:
        by_unit: dict[str, list[cp_model.IntVar]] = {u.id: [] for u in ctx.problem.lesson_units}
        for (unit_id, _day, _period, _room), var in ctx.x.items():
            by_unit[unit_id].append(var)
        for variables in by_unit.values():
            # Danh sách rỗng (không có phòng hợp lệ) làm mô hình vô nghiệm, đúng mong muốn.
            ctx.model.add_exactly_one(variables)


class RoomNoOverlapEncoder:
    """Một phòng, một ô thời gian chỉ có tối đa một đơn vị học."""

    name = "room_no_overlap"

    def encode(self, ctx: ModelContext) -> None:
        _at_most_one_per_group(ctx, lambda k: (k[3], k[1], k[2]))


class TeacherNoOverlapEncoder:
    """Một giáo viên, một ô thời gian chỉ dạy tối đa một đơn vị học."""

    name = "teacher_no_overlap"

    def encode(self, ctx: ModelContext) -> None:
        teacher_of = {u.id: u.teacher_id for u in ctx.problem.lesson_units}
        _at_most_one_per_group(ctx, lambda k: (teacher_of[k[0]], k[1], k[2]))


class ClassNoOverlapEncoder:
    """Một lớp, một ô thời gian chỉ học tối đa một đơn vị học."""

    name = "class_no_overlap"

    def encode(self, ctx: ModelContext) -> None:
        class_of = {u.id: u.class_id for u in ctx.problem.lesson_units}
        _at_most_one_per_group(ctx, lambda k: (class_of[k[0]], k[1], k[2]))

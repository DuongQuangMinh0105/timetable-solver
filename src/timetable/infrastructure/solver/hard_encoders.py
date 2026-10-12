from collections import defaultdict
from collections.abc import Callable

from ortools.sat.python import cp_model

from timetable.infrastructure.solver.encoder import ModelContext, VarKey

Occupancy = dict[tuple[str, int, int], list[cp_model.IntVar]]


def occupancy_groups(ctx: ModelContext, owner_of: Callable[[VarKey], str]) -> Occupancy:
    """Gom các biến bắt đầu theo (chủ thể, ngày, tiết bị chiếm).

    Một đơn vị học dài `duration` tiết bắt đầu ở tiết p chiếm các tiết p, p+1, ...
    nên biến của nó có mặt trong `duration` nhóm liền nhau.
    """
    duration_of = {u.id: u.duration for u in ctx.problem.lesson_units}
    groups: Occupancy = defaultdict(list)
    for key, var in ctx.s.items():
        unit_id, day, start, _room = key
        owner = owner_of(key)
        for period in range(start, start + duration_of[unit_id]):
            groups[(owner, day, period)].append(var)
    return groups


def _at_most_one_per_group(ctx: ModelContext, owner_of: Callable[[VarKey], str]) -> None:
    for variables in occupancy_groups(ctx, owner_of).values():
        if len(variables) > 1:
            ctx.model.add_at_most_one(variables)


class EachUnitOnceEncoder:
    """Mỗi đơn vị học được xếp vào đúng một ô bắt đầu (ngày, tiết, phòng)."""

    name = "each_unit_once"

    def encode(self, ctx: ModelContext) -> None:
        by_unit: dict[str, list[cp_model.IntVar]] = {u.id: [] for u in ctx.problem.lesson_units}
        for (unit_id, _day, _period, _room), var in ctx.s.items():
            by_unit[unit_id].append(var)
        for variables in by_unit.values():
            # Danh sách rỗng (không có phòng hay ô hợp lệ) làm mô hình vô nghiệm, đúng mong muốn.
            ctx.model.add_exactly_one(variables)


class RoomNoOverlapEncoder:
    """Một phòng, một tiết chỉ có tối đa một đơn vị học (tính cả các tiết bị chiếm)."""

    name = "room_no_overlap"

    def encode(self, ctx: ModelContext) -> None:
        _at_most_one_per_group(ctx, lambda k: k[3])


class TeacherNoOverlapEncoder:
    """Một giáo viên, một tiết chỉ dạy tối đa một đơn vị học (tính cả các tiết bị chiếm)."""

    name = "teacher_no_overlap"

    def encode(self, ctx: ModelContext) -> None:
        teacher_of = {u.id: u.teacher_id for u in ctx.problem.lesson_units}
        _at_most_one_per_group(ctx, lambda k: teacher_of[k[0]])


class ClassNoOverlapEncoder:
    """Một lớp, một tiết chỉ học tối đa một đơn vị học (tính cả các tiết bị chiếm)."""

    name = "class_no_overlap"

    def encode(self, ctx: ModelContext) -> None:
        class_of = {u.id: u.class_id for u in ctx.problem.lesson_units}
        _at_most_one_per_group(ctx, lambda k: class_of[k[0]])


class MaxConsecutiveEncoder:
    """Một lớp không học liên tiếp quá `Problem.max_consecutive_periods` tiết trong một ngày.

    Đếm theo số thứ tự tiết (nghỉ trưa không làm đứt chuỗi) và theo các tiết **bị chiếm**, nên
    block 2 tiết tính là 2 tiết. Chỉ áp dụng cho lớp, không áp dụng cho giáo viên.
    busy[c, d, p] = 1 nếu lớp c có tiết học ở ngày d, tiết p; với mỗi cửa sổ (max + 1) tiết
    liền nhau đều được phép xếp, tổng busy <= max.
    """

    name = "max_consecutive_periods"

    def encode(self, ctx: ModelContext) -> None:
        max_run = ctx.problem.max_consecutive_periods
        allowed = set(ctx.problem.grid.allowed_periods)
        class_of = {u.id: u.class_id for u in ctx.problem.lesson_units}

        busy: dict[tuple[str, int, int], cp_model.IntVar] = {}
        for key, variables in occupancy_groups(ctx, lambda k: class_of[k[0]]).items():
            if len(variables) == 1:
                busy[key] = variables[0]
            else:
                flag = ctx.model.new_bool_var(f"busy_{key[0]}_{key[1]}_{key[2]}")
                ctx.model.add_max_equality(flag, variables)  # flag = OR(variables)
                busy[key] = flag

        for class_id, day in {(c, d) for (c, d, _p) in busy}:
            for start in sorted(allowed):
                window_periods = range(start, start + max_run + 1)
                if not all(p in allowed for p in window_periods):
                    continue  # một tiết bị cấm làm đứt chuỗi
                window = [
                    busy[(class_id, day, p)] for p in window_periods if (class_id, day, p) in busy
                ]
                if len(window) > max_run:
                    ctx.model.add(sum(window) <= max_run)

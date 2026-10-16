"""Encoder tối ưu (tùy chọn): phá đối xứng và ràng buộc suy ra.

Các encoder này **không đổi tập nghiệm hợp lệ** (mọi lịch hợp lệ vẫn biểu diễn được, chỉ bớt các
bản sao đối xứng) nên chỉ làm solver tìm và chứng minh nhanh hơn. Chúng không nằm trong
`default_hard_encoders()`; truyền qua `optimization_encoders()` vào `build_model`.
"""

from collections import defaultdict
from collections.abc import Collection

from ortools.sat.python import cp_model

from timetable.domain.entities import LessonUnit, Room
from timetable.domain.services.block_capacity import day_patterns
from timetable.domain.services.room_policy import allowed_rooms_by_unit
from timetable.infrastructure.solver.encoder import ConstraintEncoder, ModelContext


def optimization_encoders(excluded_room_ids: Collection[str] = ()) -> list[ConstraintEncoder]:
    """Bộ encoder tối ưu, theo thứ tự áp dụng.

    `excluded_room_ids`: các phòng mà hàm mục tiêu hoặc ràng buộc nhắc tên riêng (ví dụ G316),
    không được coi là hoán đổi được với phòng khác.
    """
    return [
        IdenticalUnitOrderEncoder(),
        RoomValuePrecedenceEncoder(excluded_room_ids),
        ClassDayCapacityEncoder(),
    ]


def _unit_key(u: LessonUnit) -> tuple[str, str, str, int, str]:
    return (u.course_id, u.class_id, u.teacher_id, u.duration, u.required_room_type)


class IdenticalUnitOrderEncoder:
    """Các ca học giống hệt nhau (cùng môn, lớp, giáo viên, độ dài, loại phòng) xếp theo thứ tự.

    Hai ca như vậy hoán đổi được cho nhau mà không đổi bất kỳ ràng buộc hay điểm phạt nào (điểm
    phạt của P2 tính theo môn, không theo ca). Ép ca đứng trước bắt đầu sớm hơn ca đứng sau để
    loại các nghiệm chỉ khác nhau do hoán đổi.
    """

    name = "identical_unit_order"

    def encode(self, ctx: ModelContext) -> None:
        periods = ctx.problem.grid.periods
        start: dict[str, list[cp_model.LinearExpr]] = defaultdict(list)
        for (unit_id, day, period, _room), var in ctx.s.items():
            start[unit_id].append(var * (day * periods + period))
        groups: dict[tuple[str, str, str, int, str], list[LessonUnit]] = defaultdict(list)
        for u in ctx.problem.lesson_units:
            groups[_unit_key(u)].append(u)
        for units in groups.values():
            ordered = sorted(units, key=lambda u: u.index)
            for before, after in zip(ordered, ordered[1:], strict=False):
                if start[before.id] and start[after.id]:
                    # Hai ca cùng lớp không thể bắt đầu cùng lúc nên dùng bất đẳng thức chặt.
                    ctx.model.add(sum(start[before.id]) < sum(start[after.id]))


def _room_group_key(room: Room) -> tuple[int, str, tuple[str, ...]]:
    return (room.capacity, room.room_type, tuple(sorted(room.also_supports)))


class RoomValuePrecedenceEncoder:
    """Phá đối xứng giữa các phòng giống hệt nhau bằng ràng buộc thứ tự dùng phòng.

    Các phòng cùng sức chứa, loại phòng và loại hỗ trợ hoán đổi được cho nhau trên toàn bộ mô
    hình. Ta ép phòng thứ j chỉ được dùng sau khi phòng thứ j-1 đã được một ca đứng trước (theo
    thứ tự ca cố định) dùng, nên mỗi lịch chỉ còn một cách gán nhãn phòng.

    Chỉ đúng khi mọi ràng buộc và điểm phạt đối xứng theo hoán đổi phòng trong nhóm. Phòng mà hàm
    mục tiêu hoặc ràng buộc nhắc tên riêng phải được liệt kê trong `excluded_room_ids` để không
    vào nhóm nào (với dữ liệu thật G316 và G313 là loại phòng khác nên tự nhiên đã tách nhóm).
    Nhóm nào không thỏa điều kiện hoán đổi hoàn toàn sẽ bị bỏ qua.
    """

    name = "room_value_precedence"

    def __init__(self, excluded_room_ids: Collection[str] = ()) -> None:
        self._excluded = frozenset(excluded_room_ids)

    def encode(self, ctx: ModelContext) -> None:
        allowed = allowed_rooms_by_unit(ctx.problem)
        groups: dict[tuple[int, str, tuple[str, ...]], list[Room]] = defaultdict(list)
        for room in ctx.problem.rooms:
            if room.id not in self._excluded:
                groups[_room_group_key(room)].append(room)

        used: dict[tuple[str, str], list[cp_model.IntVar]] = defaultdict(list)
        for (unit_id, _d, _p, room_id), var in ctx.s.items():
            used[(unit_id, room_id)].append(var)

        for rooms in groups.values():
            if len(rooms) < 2:
                continue
            ids = [r.id for r in rooms]
            members = [u for u in ctx.problem.lesson_units if allowed[u.id]]
            # Bỏ qua nhóm nếu có ca chỉ dùng được một phần nhóm (không còn hoán đổi hoàn toàn).
            relevant = [u for u in members if {r.id for r in allowed[u.id]} & set(ids)]
            if any(not set(ids) <= {r.id for r in allowed[u.id]} for u in relevant):
                continue
            for j in range(1, len(ids)):
                for i, unit in enumerate(relevant):
                    here = sum(used[(unit.id, ids[j])])
                    earlier = [sum(used[(v.id, ids[j - 1])]) for v in relevant[:i]]
                    ctx.model.add(here <= sum(earlier))


class ClassDayCapacityEncoder:
    """Ràng buộc suy ra: sức chứa của một lớp trong một ngày (từ `day_patterns`).

    Quy tắc tối đa 2 tiết liên tiếp đã kéo theo các giới hạn này, nhưng nêu tường minh dạng tổng
    tuyến tính giúp bộ giải cắt nhánh sớm: số tiết học và số block 2 tiết của một lớp trong một
    ngày không vượt mức tối đa của các cách xếp một ngày hợp lệ.
    """

    name = "class_day_capacity"

    def encode(self, ctx: ModelContext) -> None:
        patterns = day_patterns(ctx.problem)
        max_cells = max(2 * a + b for a, b in patterns)
        max_twos = max(a for a, _b in patterns)
        units = {u.id: u for u in ctx.problem.lesson_units}

        cells: dict[tuple[str, int], list[cp_model.LinearExpr]] = defaultdict(list)
        twos: dict[tuple[str, int], list[cp_model.IntVar]] = defaultdict(list)
        for (unit_id, day, _p, _r), var in ctx.s.items():
            unit = units[unit_id]
            cells[(unit.class_id, day)].append(var * unit.duration)
            if unit.duration >= 2:
                twos[(unit.class_id, day)].append(var)
        for expressions in cells.values():
            ctx.model.add(sum(expressions) <= max_cells)
        for variables in twos.values():
            ctx.model.add(sum(variables) <= max_twos)

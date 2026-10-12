from timetable.domain.services.room_policy import allowed_rooms_by_unit
from timetable.domain.services.slot_policy import allowed_starts
from timetable.infrastructure.solver.encoder import ModelContext


def create_decision_variables(ctx: ModelContext) -> None:
    """Tạo biến bắt đầu s[u, d, p, r], chỉ cho phòng hợp lệ và các ô bắt đầu hợp lệ."""
    rooms = allowed_rooms_by_unit(ctx.problem)
    for unit in ctx.problem.lesson_units:
        for slot in allowed_starts(ctx.problem, unit):
            for room in rooms[unit.id]:
                key = (unit.id, slot.day, slot.period, room.id)
                name = f"s_{unit.id}_{slot.day}_{slot.period}_{room.id}"
                ctx.s[key] = ctx.model.new_bool_var(name)

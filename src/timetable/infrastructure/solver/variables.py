from timetable.domain.services.room_policy import allowed_rooms_by_unit
from timetable.infrastructure.solver.encoder import ModelContext


def create_decision_variables(ctx: ModelContext) -> None:
    """Tạo biến x[u, d, p, r], chỉ cho phòng hợp lệ và tiết được phép."""
    allowed = allowed_rooms_by_unit(ctx.problem)
    for unit in ctx.problem.lesson_units:
        for slot in ctx.problem.grid.slots():
            for room in allowed[unit.id]:
                key = (unit.id, slot.day, slot.period, room.id)
                name = f"x_{unit.id}_{slot.day}_{slot.period}_{room.id}"
                ctx.x[key] = ctx.model.new_bool_var(name)

from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Mapping

from ortools.sat.python import cp_model

from timetable.infrastructure.solver.encoder import ModelContext

SessionKey = tuple[str, int, int, str]

# Chữ ký của `add_soft_objective` do P2 viết (tham số `weights` để mặc định).
SoftObjectiveFn = Callable[..., dict[str, object]]


class SoftObjectiveApplier:
    """Cầu nối giữa mô hình của P1 và hàm mục tiêu mềm của P2 (`ObjectiveApplier`).

    - Offering của P2 = `Course.id`. Môn tách thành nhiều ca (LessonUnit) vẫn tính là một offering,
      nên biến phiên học `s[course, d, p, r]` là tổng các biến bắt đầu của các ca cùng môn.
    - Hàm của P2 tự gọi `model.minimize`; kết quả từng số hạng được lưu ở `ctx.cost_terms`.
    """

    def __init__(
        self,
        add_soft_objective: SoftObjectiveFn,
        *,
        saturdays: Collection[int],
        mba_course_ids: Collection[str] = (),
        mba_room_id: str = "G316",
        weights: tuple[int, int, int] | None = None,
    ) -> None:
        self._fn = add_soft_objective
        self._saturdays = saturdays
        self._mba = mba_course_ids
        self._mba_room = mba_room_id
        self._weights = weights

    def apply(self, ctx: ModelContext) -> None:
        course_of = {u.id: u.course_id for u in ctx.problem.lesson_units}
        grouped: dict[SessionKey, list[cp_model.IntVar]] = defaultdict(list)
        for (unit_id, day, period, room), var in ctx.s.items():
            grouped[(course_of[unit_id], day, period, room)].append(var)

        sessions: Mapping[SessionKey, cp_model.IntVar] = {
            key: self._merge(ctx, key, variables) for key, variables in grouped.items()
        }
        offerings: Iterable[str] = sorted({course_id for course_id, *_ in sessions})
        kwargs: dict[str, object] = {}
        if self._weights is not None:
            kwargs["weights"] = self._weights
        ctx.cost_terms.update(
            self._fn(
                ctx.model,
                sessions,
                offerings,
                [r.id for r in ctx.problem.rooms],
                self._saturdays,
                self._mba,
                self._mba_room,
                **kwargs,
            )
        )

    @staticmethod
    def _merge(
        ctx: ModelContext, key: SessionKey, variables: list[cp_model.IntVar]
    ) -> cp_model.IntVar:
        if len(variables) == 1:
            return variables[0]
        merged = ctx.model.new_bool_var("sess_{}_{}_{}_{}".format(*key))
        ctx.model.add(merged == sum(variables))
        return merged

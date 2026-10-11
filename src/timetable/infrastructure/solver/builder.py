from collections.abc import Sequence

from ortools.sat.python import cp_model

from timetable.domain.entities import Problem
from timetable.infrastructure.solver.encoder import ConstraintEncoder, ModelContext
from timetable.infrastructure.solver.hard_encoders import (
    ClassNoOverlapEncoder,
    EachUnitOnceEncoder,
    RoomNoOverlapEncoder,
    TeacherNoOverlapEncoder,
)
from timetable.infrastructure.solver.variables import create_decision_variables


def default_hard_encoders() -> list[ConstraintEncoder]:
    """Các ràng buộc cứng mặc định, theo thứ tự áp dụng."""
    return [
        EachUnitOnceEncoder(),
        RoomNoOverlapEncoder(),
        TeacherNoOverlapEncoder(),
        ClassNoOverlapEncoder(),
    ]


def build_model(
    problem: Problem, encoders: Sequence[ConstraintEncoder] | None = None
) -> ModelContext:
    """Dựng mô hình CP-SAT: tạo biến rồi áp dụng lần lượt các encoder.

    Không tự thêm hàm mục tiêu. ObjectiveBuilder (P2) đọc `ctx.penalties` sau khi dựng xong.
    """
    ctx = ModelContext(problem=problem, model=cp_model.CpModel())
    create_decision_variables(ctx)
    for encoder in default_hard_encoders() if encoders is None else encoders:
        encoder.encode(ctx)
    return ctx

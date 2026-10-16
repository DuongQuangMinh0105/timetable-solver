from collections.abc import Sequence

from ortools.sat.python import cp_model

from timetable.domain.entities import Problem
from timetable.infrastructure.solver.encoder import (
    ConstraintEncoder,
    ModelContext,
    ObjectiveApplier,
)
from timetable.infrastructure.solver.hard_encoders import (
    ClassNoOverlapEncoder,
    EachUnitOnceEncoder,
    MaxConsecutiveEncoder,
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
        MaxConsecutiveEncoder(),
    ]


def build_model(
    problem: Problem,
    encoders: Sequence[ConstraintEncoder] | None = None,
    *,
    soft_encoders: Sequence[ConstraintEncoder] = (),
    objective: ObjectiveApplier | None = None,
    optimization_encoders: Sequence[ConstraintEncoder] = (),
) -> ModelContext:
    """Dựng mô hình CP-SAT.

    Thứ tự: tạo biến, ràng buộc cứng (`encoders`, mặc định là `default_hard_encoders()`),
    encoder tối ưu (`optimization_encoders`, phá đối xứng, không đổi tập nghiệm hợp lệ), ràng buộc
    mềm (`soft_encoders`, ghi `ctx.penalties`), cuối cùng hàm mục tiêu (`objective`).
    """
    ctx = ModelContext(problem=problem, model=cp_model.CpModel())
    create_decision_variables(ctx)
    for encoder in default_hard_encoders() if encoders is None else encoders:
        encoder.encode(ctx)
    for optimization in optimization_encoders:
        optimization.encode(ctx)
    for soft in soft_encoders:
        soft.encode(ctx)
    if objective is not None:
        objective.apply(ctx)
    return ctx

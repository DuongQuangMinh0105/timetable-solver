from collections.abc import Sequence
from typing import cast

from ortools.sat.python import cp_model

from timetable.application.dto.solve import SolveOptions, SolveResult, SolveStatus
from timetable.domain.entities import Assignment, Problem, Timetable
from timetable.infrastructure.solver.builder import build_model
from timetable.infrastructure.solver.encoder import ConstraintEncoder, ObjectiveApplier

_STATUS = {
    cp_model.OPTIMAL: SolveStatus.OPTIMAL,
    cp_model.FEASIBLE: SolveStatus.FEASIBLE,
    cp_model.INFEASIBLE: SolveStatus.INFEASIBLE,
    cp_model.MODEL_INVALID: SolveStatus.MODEL_INVALID,
}


class CpSatSolver:
    """Hiện thực SolverPort bằng OR-Tools CP-SAT.

    `soft_encoders` và `objective` là điểm cắm cho ràng buộc mềm và hàm mục tiêu (P2).
    """

    def __init__(
        self,
        soft_encoders: Sequence[ConstraintEncoder] = (),
        objective: ObjectiveApplier | None = None,
        optimization_encoders: Sequence[ConstraintEncoder] = (),
    ) -> None:
        self._soft_encoders = tuple(soft_encoders)
        self._optimization_encoders = tuple(optimization_encoders)
        self._objective = objective

    def solve(self, problem: Problem, options: SolveOptions) -> SolveResult:
        ctx = build_model(
            problem,
            soft_encoders=self._soft_encoders,
            objective=self._objective,
            optimization_encoders=self._optimization_encoders,
        )
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = options.time_limit_s
        solver.parameters.num_workers = options.num_workers
        solver.parameters.random_seed = options.random_seed

        status = _STATUS.get(solver.solve(ctx.model), SolveStatus.UNKNOWN)
        if status not in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE):
            return SolveResult(status=status)

        # `period` của phân công là tiết BẮT ĐẦU; đơn vị chiếm `duration` tiết từ đó.
        assignments = sorted(
            (
                Assignment(unit_id=u, day=d, period=p, room_id=r)
                for (u, d, p, r), var in ctx.s.items()
                if solver.boolean_value(var)
            ),
            key=lambda a: (a.unit_id, a.day, a.period),
        )
        objective = solver.objective_value if ctx.model.has_objective() else None
        cost_terms = {
            name: expr
            if isinstance(expr, int)
            else int(solver.value(cast(cp_model.LinearExprT, expr)))
            for name, expr in ctx.cost_terms.items()
        }
        return SolveResult(
            status=status,
            timetable=Timetable(tuple(assignments)),
            objective=objective,
            cost_terms=cost_terms,
        )

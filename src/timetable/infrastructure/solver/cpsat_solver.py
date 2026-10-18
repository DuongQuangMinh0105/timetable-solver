from collections.abc import Sequence
from typing import cast

from ortools.sat.python import cp_model

from timetable.application.dto.solve import SolveOptions, SolveResult, SolveStatus
from timetable.domain.entities import Assignment, Problem, Timetable
from timetable.domain.entities.time_grid import TimeGrid
from timetable.infrastructure.solver.builder import build_model
from timetable.infrastructure.solver.encoder import ConstraintEncoder, ObjectiveApplier
from timetable.infrastructure.solver.soft_adapter import SoftObjectiveApplier
from timetable.infrastructure.solver.soft_objective import add_soft_objective

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
    ) -> None:
        self._soft_encoders = tuple(soft_encoders)
        self._objective = objective

    def solve(self, problem: Problem, options: SolveOptions) -> SolveResult:
        objective_applier = self._objective
        if objective_applier is None:
            mba_room = next((room.id for room in problem.rooms if room.room_type == "mba"), "G316")
            mba_courses = {
                unit.course_id for unit in problem.lesson_units if unit.required_room_type == "mba"
            }
            objective_applier = SoftObjectiveApplier(
                add_soft_objective,
                saturdays=(TimeGrid.SATURDAY,) if problem.grid.days > TimeGrid.SATURDAY else (),
                mba_course_ids=mba_courses,
                mba_room_id=mba_room,
                weights=problem.soft_weights,
            )
        ctx = build_model(problem, soft_encoders=self._soft_encoders, objective=objective_applier)
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
        objective_value = solver.objective_value if ctx.model.has_objective() else None
        cost_terms = {
            name: expr
            if isinstance(expr, int)
            else int(solver.value(cast(cp_model.LinearExprT, expr)))
            for name, expr in ctx.cost_terms.items()
        }
        return SolveResult(
            status=status,
            timetable=Timetable(tuple(assignments)),
            objective=objective_value,
            cost_terms=cost_terms,
        )

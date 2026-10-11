from ortools.sat.python import cp_model

from timetable.application.dto.solve import SolveOptions, SolveResult, SolveStatus
from timetable.domain.entities import Assignment, Problem, Timetable
from timetable.infrastructure.solver.builder import build_model

_STATUS = {
    cp_model.OPTIMAL: SolveStatus.OPTIMAL,
    cp_model.FEASIBLE: SolveStatus.FEASIBLE,
    cp_model.INFEASIBLE: SolveStatus.INFEASIBLE,
    cp_model.MODEL_INVALID: SolveStatus.MODEL_INVALID,
}


class CpSatSolver:
    """Hiện thực SolverPort bằng OR-Tools CP-SAT (phiên bản tối thiểu)."""

    def solve(self, problem: Problem, options: SolveOptions) -> SolveResult:
        ctx = build_model(problem)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = options.time_limit_s
        solver.parameters.num_workers = options.num_workers
        solver.parameters.random_seed = options.random_seed

        status = _STATUS.get(solver.solve(ctx.model), SolveStatus.UNKNOWN)
        if status not in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE):
            return SolveResult(status=status)

        assignments = sorted(
            (
                Assignment(unit_id=u, day=d, period=p, room_id=r)
                for (u, d, p, r), var in ctx.x.items()
                if solver.boolean_value(var)
            ),
            key=lambda a: (a.unit_id, a.day, a.period),
        )
        return SolveResult(status=status, timetable=Timetable(tuple(assignments)))

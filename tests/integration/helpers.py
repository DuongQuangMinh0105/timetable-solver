from collections.abc import Iterable, Mapping, Sequence
from typing import TypeAlias, cast

from ortools.sat.python import cp_model

from timetable.domain.rules.soft_constraints import reference_cost
from timetable.infrastructure.solver.soft_objective import add_soft_objective

__all__ = ["reference_cost", "solve"]

STARTS = (1, 3, 5)  # start periods of 2-period blocks

ScheduleKey: TypeAlias = tuple[str, int, int, str]
CostExpression: TypeAlias = int | cp_model.LinearExpr


def _value(solver: cp_model.CpSolver, expr: CostExpression) -> int:
    if isinstance(expr, int):
        return expr
    return solver.value(expr)


def solve(
    offerings: Sequence[str],
    sessions: Mapping[str, int],
    days: Sequence[int],
    rooms: Sequence[str],
    forbidden: Iterable[ScheduleKey] = (),
    sat_days: frozenset[int] = frozenset({5}),
    mba: frozenset[str] = frozenset(),
    r_mba: str = "G316",
) -> tuple[
    cp_model.CpSolver,
    int,
    dict[str, int],
    list[ScheduleKey],
]:
    """Build a tiny model with minimal hard constraints and solve it."""
    model = cp_model.CpModel()

    assignments = {
        (u, d, p, r): model.new_bool_var(f"s_{u}_{d}_{p}_{r}")
        for u in offerings
        for d in days
        for p in STARTS
        for r in rooms
    }

    for key in forbidden:
        model.add(assignments[key] == 0)

    for offering in offerings:
        model.add(
            sum(
                variable
                for key, variable in assignments.items()
                if key[0] == offering
            )
            == sessions[offering]
        )

        for day in days:
            model.add(
                sum(
                    variable
                    for key, variable in assignments.items()
                    if key[0] == offering and key[1] == day
                )
                <= 1
            )

    for day in days:
        for period in STARTS:
            for room in rooms:
                model.add(
                    sum(
                        assignments[offering, day, period, room]
                        for offering in offerings
                    )
                    <= 1
                )

    raw_costs = add_soft_objective(
        model,
        assignments,
        offerings,
        rooms,
        sat_days,
        mba,
        r_mba,
    )

    # add_soft_objective currently exposes expressions without a sufficiently
    # precise static return type. Validate that return type at its source when
    # editing the soft-objective implementation.
    costs = cast(Mapping[str, CostExpression], raw_costs)

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = 0
    solver.parameters.num_workers = 1
    status = solver.solve(model)

    schedule = [
        key for key, variable in assignments.items() if solver.value(variable)
    ]
    cost_values = {
        name: _value(solver, expression)
        for name, expression in costs.items()
    }

    return solver, int(status), cost_values, schedule
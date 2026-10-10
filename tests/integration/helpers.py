from ortools.sat.python import cp_model

from timetable.domain.rules.soft_constraints import reference_cost  # noqa: F401
from timetable.infrastructure.solver.soft_objective import add_soft_objective

STARTS = (1, 3, 5)  # start periods of 2-period blocks


def _value(solver, expr):
    return expr if isinstance(expr, int) else solver.Value(expr)


def solve(
    offerings,
    sessions,
    days,
    rooms,
    forbidden=(),
    sat_days=frozenset({5}),
    mba=frozenset(),
    r_mba="G316",
):
    """Build a tiny model with minimal hard constraints and solve it."""
    model = cp_model.CpModel()
    s = {
        (u, d, p, r): model.NewBoolVar(f"s_{u}_{d}_{p}_{r}")
        for u in offerings
        for d in days
        for p in STARTS
        for r in rooms
    }
    for key in forbidden:
        model.Add(s[key] == 0)

    for u in offerings:
        model.Add(sum(v for k, v in s.items() if k[0] == u) == sessions[u])
        for d in days:
            model.Add(sum(v for k, v in s.items() if k[0] == u and k[1] == d) <= 1)
    for d in days:
        for p in STARTS:
            for r in rooms:
                model.Add(sum(s[u, d, p, r] for u in offerings) <= 1)

    costs = add_soft_objective(model, s, offerings, rooms, sat_days, mba, r_mba)

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = 0
    solver.parameters.num_workers = 1
    status = solver.Solve(model)

    schedule = [k for k, v in s.items() if solver.Value(v)]
    cost_values = {name: _value(solver, e) for name, e in costs.items()}
    return solver, status, cost_values, schedule

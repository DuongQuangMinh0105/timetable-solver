from ortools.sat.python import cp_model

from timetable.infrastructure.solver.unsat_core import find_conflicting_groups


def _build(conflict: bool):
    model = cp_model.CpModel()
    a, b, c = (model.NewBoolVar(n) for n in "abc")
    lits = {n: model.NewBoolVar(f"lit_{n}") for n in ("g1", "g2", "g3", "g_other")}

    model.Add(a == 1).OnlyEnforceIf(lits["g1"])
    model.Add(b == 1).OnlyEnforceIf(lits["g2"])
    if conflict:
        model.Add(a + b <= 1).OnlyEnforceIf(lits["g3"])
    model.Add(c == 1).OnlyEnforceIf(lits["g_other"])
    return model, lits


def test_core_contains_all_conflicting_groups():
    model, lits = _build(conflict=True)
    status, core = find_conflicting_groups(model, lits)
    assert status == cp_model.INFEASIBLE
    assert {"g1", "g2", "g3"} <= set(core)


def test_feasible_model_returns_empty_core():
    model, lits = _build(conflict=False)
    status, core = find_conflicting_groups(model, lits)
    assert status != cp_model.INFEASIBLE
    assert core == []

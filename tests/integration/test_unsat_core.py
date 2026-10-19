from ortools.sat.python import cp_model

from timetable.infrastructure.solver.unsat_core import find_conflicting_groups


def _build(
    conflict: bool,
) -> tuple[cp_model.CpModel, dict[str, cp_model.IntVar]]:
    model = cp_model.CpModel()

    a, b, c = (model.new_bool_var(name) for name in "abc")
    literals = {
        name: model.new_bool_var(f"lit_{name}")
        for name in ("g1", "g2", "g3", "g_other")
    }

    model.add(a == 1).only_enforce_if(literals["g1"])
    model.add(b == 1).only_enforce_if(literals["g2"])

    if conflict:
        model.add(a + b <= 1).only_enforce_if(literals["g3"])

    model.add(c == 1).only_enforce_if(literals["g_other"])

    return model, literals


def test_core_contains_all_conflicting_groups() -> None:
    model, literals = _build(conflict=True)

    status, core = find_conflicting_groups(model, literals)

    assert status == cp_model.INFEASIBLE
    assert {"g1", "g2", "g3"} <= set(core)


def test_feasible_model_returns_empty_core() -> None:
    model, literals = _build(conflict=False)

    status, core = find_conflicting_groups(model, literals)

    assert status != cp_model.INFEASIBLE
    assert core == []
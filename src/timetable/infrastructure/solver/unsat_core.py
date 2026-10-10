"""Find which groups of hard constraints conflict, using CP-SAT assumptions.

Usage (P1 must follow this when adding hard constraints):

    lit = model.new_bool_var("group_room_clash")
    model.add(...).OnlyEnforceIf(lit)      # every constraint of the group
    group_literals["room_clash"] = lit
"""

from __future__ import annotations

from collections.abc import Mapping

from ortools.sat.python import cp_model


def find_conflicting_groups(
    model: cp_model.CpModel,
    group_literals: Mapping[str, cp_model.IntVar],
    time_limit_s: float = 30.0,
) -> tuple[int, list[str]]:
    """Return (solver status, names of groups in an infeasibility core).

    The core is sufficient to explain infeasibility but is not guaranteed
    to be minimal. Returns an empty list if the model is not INFEASIBLE.
    """
    name_by_index = {lit.Index(): name for name, lit in group_literals.items()}

    model.clear_assumptions()
    model.add_assumptions(list(group_literals.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = 1

    status = solver.Solve(model)
    if status != cp_model.INFEASIBLE:
        return status, []

    core = solver.SufficientAssumptionsForInfeasibility()
    return status, sorted(name_by_index[i] for i in core if i in name_by_index)


class CpSatInfeasibilityDiagnoser:
    """Adapter that implements the application-layer port."""

    def __init__(
        self,
        model: cp_model.CpModel,
        group_literals: Mapping[str, cp_model.IntVar],
        time_limit_s: float = 30.0,
    ) -> None:
        self._model = model
        self._group_literals = group_literals
        self._time_limit_s = time_limit_s

    def conflicting_groups(self) -> list[str]:
        _status, groups = find_conflicting_groups(
            self._model, self._group_literals, self._time_limit_s
        )
        return groups

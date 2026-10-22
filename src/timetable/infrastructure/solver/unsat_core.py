"""Find which groups of hard constraints conflict, using CP-SAT assumptions.

Usage (P1 must follow this when adding hard constraints):

    lit = model.new_bool_var("group_room_clash")
    model.add(...).OnlyEnforceIf(lit)      # every constraint of the group
    group_literals["room_clash"] = lit
"""

from __future__ import annotations

import time
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
    names = sorted(name_by_index[i] for i in core if i in name_by_index)
    return status, minimize_core(model, group_literals, names, time_limit_s)


MAX_CORE_TO_MINIMIZE = 40
PER_SOLVE_LIMIT_S = 2.0


def minimize_core(
    model: cp_model.CpModel,
    group_literals: Mapping[str, cp_model.IntVar],
    core: list[str],
    time_limit_s: float,
) -> list[str]:
    """Thu nhỏ lõi bằng cách thử bỏ từng nhóm: bỏ được mà vẫn vô nghiệm thì nhóm đó thừa.

    Lõi do CP-SAT trả về chỉ đủ để giải thích vô nghiệm, không tối thiểu. Bước này tốn thêm
    vài lần giải nhỏ nên bị chặn bởi kích thước lõi và `time_limit_s`; hết hạn mức thì giữ nguyên.
    """
    if len(core) > MAX_CORE_TO_MINIMIZE:
        return core
    deadline = time.monotonic() + time_limit_s
    current = list(core)
    for name in list(core):
        if time.monotonic() >= deadline:
            break
        trial = [n for n in current if n != name]
        if not trial:
            continue
        model.clear_assumptions()
        model.add_assumptions([group_literals[n] for n in trial])
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = min(PER_SOLVE_LIMIT_S, deadline - time.monotonic())
        solver.parameters.num_workers = 1
        if solver.solve(model) == cp_model.INFEASIBLE:
            current = trial
    return sorted(current)


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

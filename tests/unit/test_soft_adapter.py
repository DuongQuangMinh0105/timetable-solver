from collections.abc import Collection, Iterable, Mapping
from dataclasses import replace

from ortools.sat.python import cp_model

from solver_helpers import OPTIONS, check_valid, make_problem, unit
from timetable.domain.entities import Room
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.soft_adapter import SoftObjectiveApplier

SessionKey = tuple[str, int, int, str]


def p2_add_soft_objective(  # bản sao hàm của P2 đềEkiểm thử bềEchuyển đổi
    model: cp_model.CpModel,
    s: Mapping[SessionKey, cp_model.IntVar],
    offerings: Iterable[str],
    rooms: Collection[str],
    sat_days: Collection[int],
    mba: Collection[str],
    r_mba: str,
    weights: tuple[int, int, int] = (5, 10, 2),
) -> dict[str, object]:
    w_room, w_sat, w_g316 = weights
    offerings = list(offerings)
    use = {(u, r): model.new_bool_var(f"use_{u}_{r}") for u in offerings for r in rooms}
    for (u, _d, _p, r), var in s.items():
        model.add(var <= use[u, r])
    extra = {}
    for u in offerings:
        extra[u] = model.new_int_var(0, len(rooms), f"extra_{u}")
        model.add(extra[u] >= sum(use[u, r] for r in rooms) - 1)
    room_cost = w_room * sum(extra.values())
    sat_cost = w_sat * sum(v for (_u, d, _p, _r), v in s.items() if d in sat_days)
    g316_cost = w_g316 * sum(v for (u, _d, _p, r), v in s.items() if r == r_mba and u not in mba)
    model.minimize(room_cost + sat_cost + g316_cost)
    return {"room": room_cost, "sat": sat_cost, "g316": g316_cost}


def test_soft_objective_prefers_weekday_and_non_g316() -> None:
    from solver_helpers import one_day_grid  # noqa: F401
    from timetable.domain.entities import TimeGrid

    grid = TimeGrid(days=2, periods=8, allowed_periods=(0, 1))
    rooms = (Room("G316", "G316", 30), Room("R1", "R1", 30))
    units = [unit("a", "C", "T", duration=2)]
    problem = make_problem(units, rooms=rooms, grid=grid, block_starts=(0,))
    applier = SoftObjectiveApplier(p2_add_soft_objective, saturdays=(1,), mba_room_id="G316")
    solver = CpSatSolver(objective=applier)
    result = solver.solve(problem, OPTIONS)
    assert result.timetable is not None
    check_valid(problem, result.timetable)
    a = result.timetable.assignments[0]
    assert (a.day, a.room_id) == (0, "R1")
    assert result.objective == 0
    assert result.cost_terms == {"room": 0, "sat": 0, "g316": 0}


def test_course_with_two_units_keeps_one_room() -> None:
    from timetable.domain.entities import Course, LessonUnit, TimeGrid

    grid = TimeGrid(days=2, periods=8, allowed_periods=(0, 1, 2, 3))
    rooms = (Room("R1", "R1", 30), Room("R2", "R2", 30))
    units = [
        LessonUnit("M-0", "M", "C", "T", 0, "standard", 2),
        LessonUnit("M-1", "M", "C", "T", 1, "standard", 2),
    ]
    problem = replace(
        make_problem(units, rooms=rooms, grid=grid, block_starts=(0, 2)),
        courses=(Course("M", "M", "C", "T", 4),),
    )
    applier = SoftObjectiveApplier(p2_add_soft_objective, saturdays=())
    result = CpSatSolver(objective=applier).solve(problem, OPTIONS)
    assert result.timetable is not None
    assert len({a.room_id for a in result.timetable.assignments}) == 1
    assert result.cost_terms["room"] == 0

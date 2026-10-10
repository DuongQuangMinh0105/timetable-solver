from helpers import reference_cost, solve
from ortools.sat.python import cp_model

from timetable.domain.rules.soft_constraints import W_G316, W_ROOM, W_SAT


def test_room_stability_keeps_one_room():
    _, status, c, _ = solve(["A"], {"A": 3}, [0, 1, 2], ["R1", "R2"])
    assert status == cp_model.OPTIMAL
    assert c["room"] == 0


def test_room_stability_forced_change():
    forbidden = [("A", 1, p, "R1") for p in (1, 3, 5)] + [("A", 0, p, "R2") for p in (1, 3, 5)]
    _, status, c, _ = solve(["A"], {"A": 2}, [0, 1], ["R1", "R2"], forbidden=forbidden)
    assert status == cp_model.OPTIMAL
    assert c["room"] == W_ROOM


def test_saturday_counts_session_once():
    forbidden = [("A", 0, p, "R1") for p in (1, 3, 5)]
    _, _, c, _ = solve(["A"], {"A": 1}, [0, 5], ["R1"], forbidden=forbidden)
    assert c["sat"] == W_SAT


def test_saturday_avoided_when_possible():
    _, _, c, _ = solve(["A"], {"A": 1}, [0, 5], ["R1"])
    assert c["sat"] == 0


def test_non_mba_avoids_g316():
    _, _, c, _ = solve(["A"], {"A": 1}, [0], ["G316", "G317"])
    assert c["g316"] == 0


def test_non_mba_in_g316_when_forced():
    forbidden = [("A", 0, p, "G317") for p in (1, 3, 5)]
    _, _, c, _ = solve(["A"], {"A": 1}, [0], ["G316", "G317"], forbidden=forbidden)
    assert c["g316"] == W_G316


def test_mba_in_g316_has_no_penalty():
    _, _, c, _ = solve(["M"], {"M": 1}, [0], ["G316"], mba=frozenset({"M"}))
    assert c["g316"] == 0


def test_objective_matches_independent_calculation():
    solver, status, c, schedule = solve(
        ["A", "B"], {"A": 2, "B": 2}, [0, 1, 5], ["G316", "R1", "R2"]
    )
    assert status == cp_model.OPTIMAL
    ref = reference_cost(schedule, frozenset({5}), frozenset(), "G316")
    assert c == ref
    assert solver.ObjectiveValue() == sum(ref.values())

from helpers import reference_cost, solve
from ortools.sat.python import cp_model

from timetable.domain.rules.soft_constraints import W_G316, W_ROOM, W_SAT


def test_room_stability_keeps_one_room() -> None:
    _, status, costs, _ = solve(
        ["A"],
        {"A": 3},
        [0, 1, 2],
        ["R1", "R2"],
    )

    assert status == cp_model.OPTIMAL
    assert costs["room"] == 0


def test_room_stability_forced_change() -> None:
    forbidden = [
        ("A", 1, period, "R1")
        for period in (1, 3, 5)
    ] + [
        ("A", 0, period, "R2")
        for period in (1, 3, 5)
    ]

    _, status, costs, _ = solve(
        ["A"],
        {"A": 2},
        [0, 1],
        ["R1", "R2"],
        forbidden=forbidden,
    )

    assert status == cp_model.OPTIMAL
    assert costs["room"] == W_ROOM


def test_saturday_counts_session_once() -> None:
    forbidden = [
        ("A", 0, period, "R1")
        for period in (1, 3, 5)
    ]

    _, _, costs, _ = solve(
        ["A"],
        {"A": 1},
        [0, 5],
        ["R1"],
        forbidden=forbidden,
    )

    assert costs["sat"] == W_SAT


def test_saturday_avoided_when_possible() -> None:
    _, _, costs, _ = solve(
        ["A"],
        {"A": 1},
        [0, 5],
        ["R1"],
    )

    assert costs["sat"] == 0


def test_non_mba_avoids_g316() -> None:
    _, _, costs, _ = solve(
        ["A"],
        {"A": 1},
        [0],
        ["G316", "G317"],
    )

    assert costs["g316"] == 0


def test_non_mba_in_g316_when_forced() -> None:
    forbidden = [
        ("A", 0, period, "G317")
        for period in (1, 3, 5)
    ]

    _, _, costs, _ = solve(
        ["A"],
        {"A": 1},
        [0],
        ["G316", "G317"],
        forbidden=forbidden,
    )

    assert costs["g316"] == W_G316


def test_mba_in_g316_has_no_penalty() -> None:
    _, _, costs, _ = solve(
        ["M"],
        {"M": 1},
        [0],
        ["G316"],
        mba=frozenset({"M"}),
    )

    assert costs["g316"] == 0


def test_objective_matches_independent_calculation() -> None:
    solver, status, costs, schedule = solve(
        ["A", "B"],
        {"A": 2, "B": 2},
        [0, 1, 5],
        ["G316", "R1", "R2"],
    )

    assert status == cp_model.OPTIMAL

    reference = reference_cost(
        schedule,
        frozenset({5}),
        frozenset(),
        "G316",
    )

    assert costs == reference
    assert solver.objective_value == sum(reference.values())
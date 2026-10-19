from timetable.domain.rules.soft_constraints import (
    W_G316,
    W_ROOM,
    W_SAT,
    reference_cost,
)

SCHEDULE: list[tuple[str, int, int, str]] = [
    ("A", 0, 1, "R1"),
    ("A", 1, 1, "R2"),
    ("B", 5, 1, "G316"),
]


def test_all_three_penalties() -> None:
    cost = reference_cost(SCHEDULE, {5}, set(), "G316")
    assert cost == {"room": W_ROOM, "sat": W_SAT, "g316": W_G316}


def test_mba_in_g316_not_penalized() -> None:
    cost = reference_cost(SCHEDULE, {5}, {"B"}, "G316")
    assert cost["g316"] == 0


def test_empty_schedule() -> None:
    assert reference_cost([], {5}, set(), "G316") == {
        "room": 0,
        "sat": 0,
        "g316": 0,
    }


def test_default_weights_are_positive() -> None:
    assert W_ROOM > 0
    assert W_SAT > 0
    assert W_G316 > 0


def test_g316_penalty_is_applied_with_default_weights() -> None:
    schedule: list[tuple[str, int, int, str]] = [("B", 1, 1, "MBA_ROOM")]
    cost = reference_cost(
        schedule,
        sat_days=set(),
        mba=set(),
        r_mba="MBA_ROOM",
    )
    assert cost["g316"] > 0


def test_accepts_one_shot_iterator() -> None:
    schedule: list[tuple[str, int, int, str]] = [
        ("A", 1, 1, "R1"),
        ("A", 2, 1, "R2"),
        ("B", 6, 1, "MBA_ROOM"),
    ]

    from_list = reference_cost(
        schedule,
        sat_days={6},
        mba=set(),
        r_mba="MBA_ROOM",
    )
    from_iter = reference_cost(
        iter(schedule),
        sat_days={6},
        mba=set(),
        r_mba="MBA_ROOM",
    )

    assert from_iter == from_list
    assert from_iter == {"room": W_ROOM, "sat": W_SAT, "g316": W_G316}

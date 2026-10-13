from timetable.domain.rules.soft_constraints import (
    W_G316,
    W_ROOM,
    W_SAT,
    reference_cost,
)

SCHEDULE = [("A", 0, 1, "R1"), ("A", 1, 1, "R2"), ("B", 5, 1, "G316")]


def test_all_three_penalties():
    cost = reference_cost(SCHEDULE, {5}, set(), "G316")
    assert cost == {"room": W_ROOM, "sat": W_SAT, "g316": W_G316}


def test_mba_in_g316_not_penalized():
    cost = reference_cost(SCHEDULE, {5}, {"B"}, "G316")
    assert cost["g316"] == 0


def test_empty_schedule():
    assert reference_cost([], {5}, set(), "G316") == {"room": 0, "sat": 0, "g316": 0}


def test_default_weights_are_positive():
    assert W_ROOM > 0
    assert W_SAT > 0
    assert W_G316 > 0


def test_g316_penalty_is_applied_with_default_weights():
    # Non-MBA offering placed in the MBA room must be penalised.
    schedule = [("B", 1, 1, "MBA_ROOM")]
    cost = reference_cost(schedule, sat_days=set(), mba=set(), r_mba="MBA_ROOM")
    assert cost["g316"] > 0


def test_accepts_one_shot_iterator():
    schedule = [
        ("A", 1, 1, "R1"),
        ("A", 2, 1, "R2"),  # A uses 2 rooms -> room penalty
        ("B", 6, 1, "MBA_ROOM"),  # Saturday + non-MBA in MBA room
    ]
    kwargs = {"sat_days": {6}, "mba": set(), "r_mba": "MBA_ROOM"}

    from_list = reference_cost(schedule, **kwargs)
    from_iter = reference_cost(iter(schedule), **kwargs)

    assert from_iter == from_list
    assert from_iter == {"room": W_ROOM, "sat": W_SAT, "g316": W_G316}

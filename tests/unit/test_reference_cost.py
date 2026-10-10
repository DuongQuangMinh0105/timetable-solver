from timetable.domain.rules.soft_constraints import W_G316, W_ROOM, W_SAT, reference_cost

SCHEDULE = [("A", 0, 1, "R1"), ("A", 1, 1, "R2"), ("B", 5, 1, "G316")]


def test_all_three_penalties():
    cost = reference_cost(SCHEDULE, {5}, set(), "G316")
    assert cost == {"room": W_ROOM, "sat": W_SAT, "g316": W_G316}


def test_mba_in_g316_not_penalized():
    cost = reference_cost(SCHEDULE, {5}, {"B"}, "G316")
    assert cost["g316"] == 0


def test_empty_schedule():
    assert reference_cost([], {5}, set(), "G316") == {"room": 0, "sat": 0, "g316": 0}

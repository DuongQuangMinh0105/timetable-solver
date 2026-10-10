"""Soft-constraint weights and an independent penalty calculator."""

from __future__ import annotations

from collections.abc import Collection, Iterable

W_ROOM = 5
W_SAT = 10
W_G316 = 2

# One scheduled session = (offering, day, start_period, room)
Session = tuple[str, int, int, str]


def reference_cost(
    schedule: Iterable[Session],
    sat_days: Collection[int],
    mba: Collection[str],
    r_mba: str,
    weights: tuple[int, int, int] = (W_ROOM, W_SAT, W_G316),
) -> dict[str, int]:
    """Compute penalties directly from a schedule, without any solver.

    Used as an independent check against the solver's objective value.
    """
    w_room, w_sat, w_g316 = weights
    schedule = list(schedule)

    rooms_of: dict[str, set[str]] = {}
    for u, _d, _p, r in schedule:
        rooms_of.setdefault(u, set()).add(r)

    return {
        "room": w_room * sum(len(rs) - 1 for rs in rooms_of.values()),
        "sat": w_sat * sum(1 for _u, d, _p, _r in schedule if d in sat_days),
        "g316": w_g316 * sum(1 for u, _d, _p, r in schedule if r == r_mba and u not in mba),
    }

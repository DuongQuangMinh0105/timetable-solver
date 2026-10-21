"""Soft-constraint weights and an independent penalty calculator."""

from __future__ import annotations

from collections.abc import Collection, Iterable

W_ROOM = 5
W_SAT = 10
W_G316 = 2

SOFT_WEIGHT_DEFAULTS = {
    "room_stability": W_ROOM,
    "avoid_saturday": W_SAT,
    "reserve_mba_room": W_G316,
}
SOFT_WEIGHT_KEYS = frozenset(SOFT_WEIGHT_DEFAULTS)

# One scheduled session = (offering, day, start_period, room)
Session = tuple[str, int, int, str]


def parse_soft_weights(config: object) -> tuple[int, int, int]:
    """Validate and order the supported nonnegative integer soft-constraint weights."""
    if not isinstance(config, dict):
        raise ValueError("soft_weights must be an object")

    unsupported = set(config) - SOFT_WEIGHT_KEYS
    if unsupported:
        raise ValueError(f"Unsupported soft_weights keys: {sorted(unsupported)}")

    weights: dict[str, int] = {}
    for key, default in SOFT_WEIGHT_DEFAULTS.items():
        value = config.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"soft_weights.{key} must be an integer")
        if value < 0:
            raise ValueError(f"soft_weights.{key} must be nonnegative")
        weights[key] = value

    return (
        weights["room_stability"],
        weights["avoid_saturday"],
        weights["reserve_mba_room"],
    )


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

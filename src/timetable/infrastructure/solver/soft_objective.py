"""Adds the soft-constraint objective to a CP-SAT model."""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping

from ortools.sat.python import cp_model

from timetable.domain.rules.soft_constraints import W_G316, W_ROOM, W_SAT

SessionKey = tuple[str, int, int, str]  # (offering, day, start_period, room)


def add_soft_objective(
    model: cp_model.CpModel,
    s: Mapping[SessionKey, cp_model.IntVar],
    offerings: Iterable[str],
    rooms: Collection[str],
    sat_days: Collection[int],
    mba: Collection[str],
    r_mba: str,
    weights: tuple[int, int, int] = (W_ROOM, W_SAT, W_G316),
) -> dict[str, object]:
    """Create the objective and return each cost term separately.

    `s[(u, d, p, r)]` = 1 if a 2-period session of offering `u` starts at
    day `d`, period `p`, room `r`. This function calls model.minimize();
    nobody else should call it afterwards (the last call wins).
    """
    w_room, w_sat, w_g316 = weights
    offerings = list(offerings)

    use = {(u, r): model.new_bool_var(f"use_{u}_{r}") for u in offerings for r in rooms}
    for (u, _d, _p, r), var in s.items():
        model.add(var <= use[u, r])

    extra = {}
    for u in offerings:
        extra[u] = model.new_int_var(0, len(rooms), f"extra_rooms_{u}")
        model.add(extra[u] >= sum(use[u, r] for r in rooms) - 1)

    room_cost = w_room * sum(extra.values())
    sat_cost = w_sat * sum(v for (_u, d, _p, _r), v in s.items() if d in sat_days)
    g316_cost = w_g316 * sum(v for (u, _d, _p, r), v in s.items() if r == r_mba and u not in mba)

    model.minimize(room_cost + sat_cost + g316_cost)
    return {"room": room_cost, "sat": sat_cost, "g316": g316_cost}

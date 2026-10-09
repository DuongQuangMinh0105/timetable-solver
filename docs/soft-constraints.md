# Soft Constraints

## 1. Notation

| Symbol | Meaning |
|---|---|
| `u ∈ U` | Class / unit to be scheduled |
| `d ∈ D` | Day of the week; `D_sat ⊂ D` is the set of Saturdays |
| `p ∈ P` | Period (time slot) |
| `r ∈ R` | Room |
| `x[u,d,p,r]` | BoolVar = 1 if class `u` is held on day `d`, period `p`, in room `r` |
| `use[u,r]` | BoolVar = 1 if class `u` uses room `r` in at least one period |
| `extra_rooms[u]` | IntVar ≥ 0: number of distinct rooms class `u` uses, minus 1 |

> The variable name `x[u,d,p,r]` must be agreed with P1 on day 2.

## 2. RoomStability (room-change penalty)

Link `use` to `x` (one direction is enough because the problem is a minimization):

    x[u,d,p,r] <= use[u,r]    for all u, d, p, r

Extra rooms per class:

    extra_rooms[u] = sum_r use[u,r] - 1

Assumption: every class has at least one session, so `extra_rooms[u] >= 0`.

Limitation: this penalizes the **number of distinct rooms**, not the number
of room switches between consecutive periods.

## 3. AvoidSaturday

    sat_sessions = sum_{u, d in D_sat, p, r} x[u,d,p,r]

Each session scheduled on Saturday is penalized by `W_SAT`.

## 4. Objective function

    minimize  W_ROOM * sum_u extra_rooms[u]  +  W_SAT * sat_sessions

Weights are integers (CP-SAT only supports integer coefficients).

## 5. Initial weights

| Parameter | Value | Rationale |
|---|---|---|
| `W_ROOM` | 5 | Changing rooms is a mild inconvenience, acceptable when necessary |
| `W_SAT` | 10 | Saturday classes are more inconvenient: one Saturday session equals two extra rooms |

The 2:1 ratio is a heuristic starting point with no supporting data yet.
It will be tuned after benchmarking on day 6.

## 6. Scope

This document covers soft constraints only. Hard constraints (no room
clash, no period clash, etc.) are specified in a separate document.
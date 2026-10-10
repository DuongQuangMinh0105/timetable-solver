# Soft Constraints

## 1. Notation

| Symbol | Meaning |
|---|---|
| `u ∈ U` | Offering = one class taking one subject (class-subject pair) |
| `d ∈ D` | Day of the week; `D_sat ⊂ D` is the set of Saturdays |
| `p ∈ P` | Period (time slot) |
| `r ∈ R` | Room; `r_mba` = G316 |
| `U_mba ⊂ U` | MBA offerings (must be in G316, hard constraint) |
| `s[u,d,p,r]` | BoolVar = 1 if a session of `u` **starts** at day `d`, period `p`, room `r`. One session = a block of 2 consecutive periods |
| `x[u,d,p,r]` | BoolVar = 1 if `u` is held at day `d`, period `p`, room `r` (derived from `s`) |
| `use[u,r]` | BoolVar = 1 if offering `u` uses room `r` in at least one session |
| `extra_rooms[u]` | IntVar ≥ 0: number of distinct rooms used by `u`, minus 1 |

> Variable names `x` and `s` must be agreed with P1 on day 2.
> Link between them (owned by P1): `x[u,d,p,r] = s[u,d,p,r] + s[u,d,p-1,r]`.
> The number of sessions per week is an input (`sessions_per_week[u]`), not a constant.

## 2. RoomStability

Scope: room stability is per **offering** (one subject keeps one room).
One direction of the link is enough because the problem is a minimization:

    s[u,d,p,r] <= use[u,r]          for all u, d, p, r
    extra_rooms[u] >= sum_r use[u,r] - 1
    extra_rooms[u] >= 0

Limitation: this penalizes the **number of distinct rooms**, not the number
of room switches between sessions.

## 3. AvoidSaturday

    sat_sessions = sum_{u, d in D_sat, p, r} s[u,d,p,r]

Each **session** (2-period block) on Saturday is penalized by `W_SAT`.
Counting `s` instead of `x` avoids penalizing a 2-period session twice.
Periods 7-8 are never scheduled (hard constraint).

## 4. PreferMbaRoom (G316 priority)

G316 may host regular classes but MBA has priority:

    g316_sessions = sum_{u not in U_mba, d, p} s[u,d,p,r_mba]

Each non-MBA session in G316 is penalized by `W_G316`.

## 5. Objective function

    minimize  W_ROOM  * sum_u extra_rooms[u]
            + W_SAT   * sat_sessions
            + W_G316  * g316_sessions

The solver code must return each term (`room_cost`, `sat_cost`, `g316_cost`)
separately so that a schedule's penalty can be explained and weights tuned.
Weights are integers (CP-SAT only supports integer coefficients).

## 6. Initial weights

| Parameter | Value | Rationale |
|---|---|---|
| `W_ROOM` | 5 | Changing rooms is a mild inconvenience, acceptable when necessary |
| `W_SAT` | 10 | One Saturday session equals two extra rooms |
| `W_G316` | 2 | Mild: only keeps G316 free for MBA when other rooms are available |

These ratios are heuristic starting points with no supporting data yet.
They will be tuned after benchmarking on day 6.

## 7. Hard/soft boundary

| Rule | Type |
|---|---|
| MBA offerings only in G316 | Hard |
| G313 only for Design offerings | Hard |
| G311, G312 never used for regular classes | Hard |
| No sessions in periods 7-8 | Hard |
| Class size 20-30 within room capacity | Hard |
| Non-MBA offerings in G316 | **Soft** (`W_G316`) |
| Saturday sessions | **Soft** (`W_SAT`) |
| Offering changes room | **Soft** (`W_ROOM`) |

## 8. Scope

This document covers soft constraints only. Hard constraints (no room
clash, no period clash, teacher availability, 2-period blocks, rest rule, etc.)
are specified in a separate document.
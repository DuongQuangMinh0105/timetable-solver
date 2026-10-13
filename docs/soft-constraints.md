# Soft Constraints

## 1. Overview

A soft constraint may be violated, but every violation adds a penalty to the
objective. The solver searches for the schedule with the smallest total
penalty. Hard constraints (never violated) are specified in a separate
document; section 8 only lists the boundary between the two.

| Code | Name | Constant | Weight | What is penalized |
|---|---|---|---|---|
| `room` | RoomStability | `W_ROOM` | 5 | Each extra distinct room an offering uses beyond its first |
| `sat` | AvoidSaturday | `W_SAT` | 10 | Each session scheduled on Saturday |
| `g316` | PreferMbaRoom | `W_G316` | 2 | Each session of a non-MBA offering held in G316 |

Implementation map:

| Concern | Location |
|---|---|
| Weights and independent penalty calculator (`reference_cost`) | `src/timetable/domain/rules/soft_constraints.py` |
| Objective function (`add_soft_objective`) | `infrastructure/solver/soft_objective.py` |

## 2. Calendar frame

- A teaching week runs Monday to Saturday (T2 to T7).
- A day has 8 periods:

| Period | Time |
|---|---|
| 1 | 07:30 - 09:00 |
| 2 | 09:10 - 10:40 |
| 3 | 10:50 - 12:20 |
| 4 | 12:50 - 14:20 |
| 5 | 14:30 - 16:00 |
| 6 | 16:10 - 17:40 |
| 7 | 17:50 - 19:20 |
| 8 | 19:30 - 21:00 |

- Periods 7 and 8 are never scheduled (hard constraint).
- A **session** is a block of 2 consecutive periods, identified by the period
  in which it starts.

## 3. Notation

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

Agreed with P1:

- Variable names `x` and `s` are shared between the hard model and the soft
  objective.
- The link between them is owned by P1:
  `x[u,d,p,r] = s[u,d,p,r] + s[u,d,p-1,r]`.
- The number of sessions per week is an input (`sessions_per_week[u]`), not a
  constant.

In the reference calculator a scheduled session is the tuple
`(offering, day, start_period, room)`, which corresponds to one `s[u,d,p,r] = 1`.

## 4. RoomStability

Scope: room stability is per **offering** (one subject keeps one room).
For example, if a class is studying subject A in room G502, the schedule
should keep using G502 for that class.

One direction of the link is enough because the problem is a minimization:

    s[u,d,p,r] <= use[u,r]          for all u, d, p, r
    extra_rooms[u] >= sum_r use[u,r] - 1
    extra_rooms[u] >= 0

Penalty:

    room_penalty = W_ROOM * sum_u extra_rooms[u]

| Rooms used by an offering | Penalty |
|---|---|
| 1 | 0 |
| 2 | `W_ROOM` |
| 3 | `2 * W_ROOM` |

Limitation: this penalizes the **number of distinct rooms**, not the number of
room switches between sessions. An offering that alternates between two rooms
every week is penalized the same as one that uses each room for half the term.

## 5. AvoidSaturday

    sat_sessions = sum_{u, d in D_sat, p, r} s[u,d,p,r]

Each **session** (2-period block) on Saturday is penalized by `W_SAT`.
Counting `s` instead of `x` avoids penalizing a 2-period session twice.
The set of penalized days is a parameter (`sat_days`), so the rule is not
hard-wired to a day index.

    sat_penalty = W_SAT * sat_sessions

## 6. PreferMbaRoom (G316 priority)

G316 may host regular classes, but MBA has priority and must use it. Other
offerings should only be placed there when no other room is suitable.

    g316_sessions = sum_{u not in U_mba, d, p} s[u,d,p,r_mba]
    g316_penalty  = W_G316 * g316_sessions

Each non-MBA session in G316 is penalized by `W_G316`.

## 7. Objective function

    minimize  W_ROOM  * sum_u extra_rooms[u]
            + W_SAT   * sat_sessions
            + W_G316  * g316_sessions

Requirements:

- The solver code must return each term (`room_cost`, `sat_cost`, `g316_cost`)
  separately, so that a schedule's penalty can be explained and weights tuned.
- Weights are integers, because CP-SAT only supports integer coefficients.

### Initial weights

| Parameter | Value | Rationale |
|---|---|---|
| `W_ROOM` | 5 | Changing rooms is a mild inconvenience, acceptable when necessary |
| `W_SAT` | 10 | One Saturday session equals two extra rooms |
| `W_G316` | 2 | Mild: only keeps G316 free for MBA when other rooms are available |

These ratios are heuristic starting points with no supporting data yet.
They will be tuned after benchmarking on day 6.

## 8. Hard/soft boundary

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

## 9. Verification

`reference_cost(schedule, sat_days, mba, r_mba, weights)` computes the three
penalties directly from a schedule, without any solver. It is the independent
oracle for the solver's objective value.

| `reference_cost` key | Solver term | Formula |
|---|---|---|
| `room` | `room_cost` | `W_ROOM * sum_u (distinct rooms of u - 1)` |
| `sat` | `sat_cost` | `W_SAT * (sessions on days in sat_days)` |
| `g316` | `g316_cost` | `W_G316 * (non-MBA sessions in r_mba)` |

For any feasible schedule found by the solver, the three terms must match the
output of `reference_cost` for the same schedule.

### Worked example

`sat_days = {6}`, `mba = {}`, `r_mba = "G316"`.

| Offering | Day | Start period | Room |
|---|---|---|---|
| A | 1 | 1 | R1 |
| A | 2 | 1 | R2 |
| B | 6 | 1 | G316 |

- `room`: A uses 2 rooms, so one extra room: `5 * 1 = 5`.
- `sat`: one session on day 6: `10 * 1 = 10`.
- `g316`: B is not MBA and sits in G316: `2 * 1 = 2`.
- Total penalty: **17**.

### Test coverage

`reference_cost` is covered by unit tests in `tests/unit/test_reference_cost.py`.
Mutation testing (sign flips, wrong weight order, wrong boolean operators,
changed default weights, one-shot iterator input, wrong grouping key) leaves
no surviving mutants.

## 10. Known limitations

- `room` counts distinct rooms, not room switches (see section 4).
- Weights are untuned starting values (see section 7).
- The one-directional link `s <= use` is correct only while the objective is
  minimized. If a constraint ever rewards a larger `use`, the link must become
  an equality.

## 11. Scope

This document covers soft constraints only. Hard constraints (no room clash,
no period clash, teacher availability, 2-period blocks, rest rule, etc.) are
specified in a separate document.

## Appendix: rooms with a special purpose

| Room | Purpose |
|---|---|
| G311, G312 | Event hall |
| G313 | Drawing/design room |
| G315 | Admissions counseling |
| G316 | Regular classroom; mandatory for MBA classes |
| G320 | Storage |
| G501 | Director |
| G505 | Academic Affairs Administration Dept. |
| G506 | Library |
| G507 | Student service |
"""Mini mutation tester for soft_constraints.py (works on Windows, no mutmut).

Usage (from the repo root):
    python mutate.py <path to soft_constraints.py>

Each mutant edits ONE spot, runs the unit tests, then restores the file.
KILLED   = tests failed  (good: tests caught the bug)
SURVIVED = tests passed  (bad: add a test for it)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MUTANTS: list[tuple[str, str, str]] = [
    ("01 room: len(rs)-1 -> len(rs)", "len(rs) - 1 for", "len(rs) for"),
    (
        "02 room: only penalise if >2 rooms",
        "len(rs) - 1 for",
        "(len(rs) - 1 if len(rs) > 2 else 0) for",
    ),
    ("03 sat: d in -> d not in", "if d in sat_days", "if d not in sat_days"),
    (
        "04 g316: not in mba -> in mba",
        "r == r_mba and u not in mba",
        "r == r_mba and u in mba",
    ),
    (
        "05 g316: and -> or",
        "r == r_mba and u not in mba",
        "r == r_mba or u not in mba",
    ),
    (
        "06 weights unpacked in wrong order",
        "w_room, w_sat, w_g316 = weights",
        "w_sat, w_room, w_g316 = weights",
    ),
    ("07 W_G316 = 2 -> 0", "W_G316 = 2", "W_G316 = 0"),
    (
        "09 remove list(schedule) (generator input)",
        "schedule = list(schedule)",
        "pass",
    ),
    (
        "10 rooms keyed by (offering, day)",
        "rooms_of.setdefault(u, set()).add(r)",
        "rooms_of.setdefault((u, _d), set()).add(r)",
    ),
]


def run_tests() -> bool:
    """Return True if the tests pass."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit", "-q", "-x"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python mutate.py <path to soft_constraints.py>")

    target = Path(sys.argv[1])
    original = target.read_text(encoding="utf-8")

    if not run_tests():
        sys.exit("Baseline tests are failing. Fix them before mutating.")

    results: list[tuple[str, str]] = []
    try:
        for name, old, new in MUTANTS:
            if original.count(old) != 1:
                results.append((name, f"SKIPPED (pattern found {original.count(old)}x)"))
                continue
            target.write_text(original.replace(old, new), encoding="utf-8")
            status = "SURVIVED  <-- add a test" if run_tests() else "KILLED"
            results.append((name, status))
            print(f"{name}: {status}", flush=True)
    finally:
        target.write_text(original, encoding="utf-8")

    print("\n=== SUMMARY ===")
    for name, status in results:
        print(f"{name}: {status}")


if __name__ == "__main__":
    main()

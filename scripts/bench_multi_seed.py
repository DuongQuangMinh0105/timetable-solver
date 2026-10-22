"""Benchmark đa seed: chạy nhiều seed cho mỗi profile và bộ trọng số, tính trung bình.

Chạy từ thư mục gốc repo:
    uv run python scripts/bench_multi_seed.py

Kết quả ghi vào docs/reports/multi_seed_baseline.md
"""

import json
import statistics
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from timetable.application.dto.solve import SolveOptions
from timetable.domain.entities.time_grid import TimeGrid
from timetable.domain.rules.soft_constraints import W_G316, W_ROOM, W_SAT
from timetable.infrastructure.generator import generate_profile
from timetable.infrastructure.problem_loader import load_problem
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.soft_adapter import SoftObjectiveApplier
from timetable.infrastructure.solver.soft_objective import add_soft_objective

# Cấu hình
PROFILES = ["small", "spec", "many_mba", "tight_teachers"]
SEEDS = [0, 1, 2, 3, 4]
WEIGHTS_SETS = {
    "Mặc định (5-10-2)": (W_ROOM, W_SAT, W_G316),
    "Ưu tiên tránh T7 (5-20-2)": (5, 20, 2),
    "Ưu tiên ổn định phòng (10-10-2)": (10, 10, 2),
    "Ưu tiên G316 (5-10-10)": (5, 10, 10),
}
TIME_LIMIT = 30.0
NUM_WORKERS = 2
OUTPUT_FILE = Path(__file__).parent.parent / "docs" / "reports" / "multi_seed_baseline.md"


def load_problem_by_profile(profile_name: str, seed: int) -> tuple:
    """Load problem từ generator profile với seed cụ thể."""
    data = generate_profile(profile_name, seed=seed)
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "input.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        problem = load_problem(p)
    return problem, data


def solve_problem(problem, time_limit: float, workers: int) -> dict:
    """Giải bài toán, trả về kết quả."""
    mba_room = next((r.id for r in problem.rooms if r.room_type == "mba"), "G316")
    mba_courses = {c.id for c in problem.courses if c.required_room_type == "mba"}

    objective_applier = SoftObjectiveApplier(
        add_soft_objective,
        saturdays=(TimeGrid.SATURDAY,) if problem.grid.days > TimeGrid.SATURDAY else (),
        mba_course_ids=mba_courses,
        mba_room_id=mba_room,
        weights=problem.soft_weights,
    )

    solver = CpSatSolver(objective=objective_applier)
    options = SolveOptions(time_limit_s=time_limit, num_workers=workers, random_seed=0)

    start = time.perf_counter()
    result = solver.solve(problem, options)
    elapsed = time.perf_counter() - start

    return {
        "status": str(result.status),
        "time": elapsed,
        "objective": result.objective if result.objective is not None else 0,
        "room": result.cost_terms.get("room", 0),
        "sat": result.cost_terms.get("sat", 0),
        "g316": result.cost_terms.get("g316", 0),
    }


def main():
    all_results = {}  # (profile, weights_name) -> list of results

    print("Bắt đầu Benchmark đa seed...")
    print(f"Profiles: {PROFILES}")
    print(f"Seeds: {SEEDS}")
    print(f"Weights: {list(WEIGHTS_SETS.keys())}")
    print(f"Time limit: {TIME_LIMIT}s, Workers: {NUM_WORKERS}\n")

    for profile_name in PROFILES:
        for weights_name, weights in WEIGHTS_SETS.items():
            key = (profile_name, weights_name)
            all_results[key] = []

            print(f"  Đang chạy: {profile_name} | {weights_name}")

            for seed in SEEDS:
                problem, data = load_problem_by_profile(profile_name, seed)
                problem = replace(problem, soft_weights=weights)

                res = solve_problem(problem, TIME_LIMIT, NUM_WORKERS)
                all_results[key].append(res)
                print(
                    f"    Seed {seed}: {res['status']} | "
                    f"{res['time']:.2f}s | obj={res['objective']}"
                )

    # Ghi báo cáo
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        f.write("# Báo cáo Benchmark Đa Seed (Trung bình qua 5 seeds)\n\n")
        f.write(f"- Thời gian chạy: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- Seeds: {SEEDS}\n")
        f.write(f"- Time limit: {TIME_LIMIT}s | Workers: {NUM_WORKERS}\n\n")

        f.write("## Bảng tổng hợp (Trung bình)\n\n")
        f.write(
            "| Profile | Bộ trọng số | Trạng thái trung bình | Thời gian TB (s) | "
            "Mục tiêu TB | Phạt Phòng TB | Phạt T7 TB | Phạt G316 TB |\n"
        )
        f.write("|---|---|---|---|---|---|---|---|\n")

        for profile_name in PROFILES:
            for weights_name in WEIGHTS_SETS:
                key = (profile_name, weights_name)
                results = all_results[key]

                avg_time = statistics.mean(r["time"] for r in results)
                avg_obj = statistics.mean(r["objective"] for r in results)
                avg_room = statistics.mean(r["room"] for r in results)
                avg_sat = statistics.mean(r["sat"] for r in results)
                avg_g316 = statistics.mean(r["g316"] for r in results)

                statuses = [r["status"] for r in results]
                most_common_status = max(set(statuses), key=statuses.count)

                f.write(
                    f"| {profile_name} | {weights_name} | {most_common_status} | "
                    f"{avg_time:.2f} | {avg_obj:.1f} | {avg_room:.1f} | "
                    f"{avg_sat:.1f} | {avg_g316:.1f} |\n"
                )

        f.write("\n## So sánh Trước / Sau (theo Profile)\n\n")
        f.write("So sánh bộ trọng số Mặc định (5-10-2) với các bộ khác để thấy sự đánh đổi:\n\n")

        for profile_name in PROFILES:
            f.write(f"### {profile_name}\n\n")
            f.write("| Bộ trọng số | Mục tiêu TB | Phạt Phòng TB | Phạt T7 TB | Phạt G316 TB |\n")
            f.write("|---|---|---|---|---|\n")

            for weights_name in WEIGHTS_SETS:
                key = (profile_name, weights_name)
                results = all_results[key]
                avg_obj = statistics.mean(r["objective"] for r in results)
                avg_room = statistics.mean(r["room"] for r in results)
                avg_sat = statistics.mean(r["sat"] for r in results)
                avg_g316 = statistics.mean(r["g316"] for r in results)
                f.write(
                    f"| {weights_name} | {avg_obj:.1f} | {avg_room:.1f} | "
                    f"{avg_sat:.1f} | {avg_g316:.1f} |\n"
                )
            f.write("\n")

        f.write("## Nhận xét\n\n")
        f.write("- **Độ ổn định:** (Điền nhận xét về sự biến động của objective qua các seed)\n")
        # Sửa lỗi E501: Chia nhỏ dòng 174
        f.write(
            "- **Ảnh hưởng của trọng số:** (Điền nhận xét về sự đánh đổi giữa các bộ trọng số)\n"
        )
        f.write("- **Khuyến nghị:** (Điền khuyến nghị về bộ trọng số nên dùng)\n")

    print(f"\nHoàn tất! Báo cáo tại: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

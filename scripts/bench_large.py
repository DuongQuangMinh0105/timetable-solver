"""Benchmark bài toán lớn: 50 lớp và 100 lớp, giới hạn 1 CPU (tương đương 0.1 CPU trên máy 10 nhân).

Chạy từ thư mục gốc repo:
    uv run python scripts/bench_large.py

Kết quả ghi vào docs/reports/large_scale_benchmark.md
"""

import json
import sys
import tempfile
import time
from pathlib import Path

# Thêm src vào path nếu chạy trực tiếp
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from timetable.application.dto.solve import SolveOptions
from timetable.domain.entities.time_grid import TimeGrid
from timetable.infrastructure.generator import generate_v1
from timetable.infrastructure.problem_loader import load_problem
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.soft_adapter import SoftObjectiveApplier
from timetable.infrastructure.solver.soft_objective import add_soft_objective

OUTPUT_FILE = Path(__file__).parent.parent / "docs" / "reports" / "large_scale_benchmark.md"

# Cấu hình
SCALES = [50, 100]
TIME_LIMITS = [30, 60, 120]  # Thử các mức thời gian khác nhau
NUM_WORKERS = 1  # Giới hạn 1 worker để mô phỏng 0.1 CPU


def load_problem_by_size(num_classes: int) -> tuple:
    """Load problem từ generator với số lớp tùy chỉnh."""
    # Giả sử 10% là MBA, 10% là Design
    num_mba = max(1, num_classes // 10)
    num_art = max(1, num_classes // 10)

    data = generate_v1(
        num_classes=num_classes,
        num_teachers=max(10, num_classes // 2),
        seed=0,
        num_mba_classes=num_mba,
        num_art_classes=num_art,
    )
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "input.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        problem = load_problem(p)
    return problem, data


def solve_large(problem, time_limit: float, workers: int) -> dict:
    """Giải bài toán lớn, trả về kết quả."""
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
        "objective": result.objective,
        "cost_terms": result.cost_terms,
        "num_units": len(problem.lesson_units),
    }


def main():
    results = []
    print("Bắt đầu Benchmark bài toán lớn...")

    for num_classes in SCALES:
        print(f"\n  Đang load problem {num_classes} lớp...")
        problem, data = load_problem_by_size(num_classes)
        print(f"  Số unit: {len(problem.lesson_units)}")

        for time_limit in TIME_LIMITS:
            print(f"    Chạy với time_limit={time_limit}s, workers={NUM_WORKERS}...")
            res = solve_large(problem, time_limit, NUM_WORKERS)
            print(f"      -> {res['status']} | {res['time']:.2f}s | obj={res['objective']}")

            results.append(
                {
                    "num_classes": num_classes,
                    "num_units": res["num_units"],
                    "time_limit": time_limit,
                    "workers": NUM_WORKERS,
                    "status": res["status"],
                    "time": res["time"],
                    "objective": res["objective"],
                    "cost_terms": res["cost_terms"],
                }
            )

    # Ghi báo cáo
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        f.write("# Báo cáo Benchmark Bài toán Lớn (50 và 100 lớp)\n\n")
        f.write(f"- Thời gian chạy: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- Số workers: {NUM_WORKERS} (tương đương 0.1 CPU trên máy 10 nhân)\n\n")

        f.write("## Bảng kết quả\n\n")
        f.write("| Số lớp | Số unit | Time limit (s) | Trạng thái | Thời gian (s) | Mục tiêu |\n")
        f.write("|---|---|---|---|---|---|\n")

        for r in results:
            obj = r["objective"] if r["objective"] is not None else 0
            f.write(
                f"| {r['num_classes']} | {r['num_units']} | {r['time_limit']} | "
                f"{r['status']} | {r['time']:.2f} | {obj:.0f} |\n"
            )

        f.write("\n## Nhận xét và Điểm nghẽn\n\n")
        f.write("- **50 lớp:** (Điền nhận xét dựa trên kết quả thực tế)\n")
        f.write("- **100 lớp:** (Điền nhận xét dựa trên kết quả thực tế)\n")
        f.write("- **Khuyến nghị:** (Điền khuyến nghị dựa trên kết quả thực tế)\n")

    print(f"\nHoàn tất! Báo cáo tại: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

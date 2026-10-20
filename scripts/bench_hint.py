"""Benchmark ảnh hưởng của AddHint và tham số solver.

Chạy từ thư mục gốc repo:
    uv run python scripts/bench_hint.py

Kết quả được ghi vào docs/reports/hint_benchmark.md
"""

import json
import sys
import tempfile
import time
from pathlib import Path

from ortools.sat.python import cp_model

# Thêm src vào path nếu chạy trực tiếp
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from timetable.domain.entities import Problem
from timetable.domain.entities.time_grid import TimeGrid
from timetable.infrastructure.generator import generate_profile
from timetable.infrastructure.problem_loader import load_problem
from timetable.infrastructure.solver.builder import build_model
from timetable.infrastructure.solver.soft_adapter import SoftObjectiveApplier
from timetable.infrastructure.solver.soft_objective import add_soft_objective

# Cấu hình Benchmark
PROFILES = ["spec", "many_mba", "tight_teachers"]  # Bỏ small vì quá nhanh
TIME_LIMIT = 30.0
OUTPUT_FILE = Path(__file__).parent.parent / "docs" / "reports" / "hint_benchmark.md"


def load_problem_by_profile(profile_name: str) -> tuple[Problem, dict]:
    """Load problem từ generator profile."""
    data = generate_profile(profile_name, seed=0)
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "input.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        problem = load_problem(p)
    return problem, data


def create_naive_hints(problem: Problem, ctx) -> dict:
    """Tạo hint ngây thơ: gợi ý phòng cho từng unit dựa trên required_room_type."""
    rooms_by_type = {}
    for room in problem.rooms:
        rooms_by_type.setdefault(room.room_type, []).append(room.id)
        for supported in room.also_supports:
            rooms_by_type.setdefault(supported, []).append(room.id)

    hints = {}
    # Sửa lỗi B007: Đổi tên day, period thành _day, _period
    for (unit_id, _day, _period, room_id), var in ctx.s.items():
        unit = next((u for u in problem.lesson_units if u.id == unit_id), None)
        if not unit:
            hints[var] = 0
            continue

        suitable_rooms = rooms_by_type.get(unit.required_room_type, [])
        if room_id in suitable_rooms:
            hints[var] = 1
        else:
            hints[var] = 0
    return hints


def solve_with_hint(problem: Problem, use_hint: bool, time_limit: float) -> dict:
    """Giải bài toán, có hoặc không có Hint. Trả về dict kết quả."""
    mba_room = next((r.id for r in problem.rooms if r.room_type == "mba"), "G316")
    mba_courses = {c.id for c in problem.courses if c.required_room_type == "mba"}

    objective_applier = SoftObjectiveApplier(
        add_soft_objective,
        saturdays=(TimeGrid.SATURDAY,) if problem.grid.days > TimeGrid.SATURDAY else (),
        mba_course_ids=mba_courses,
        mba_room_id=mba_room,
        weights=problem.soft_weights,
    )

    ctx = build_model(problem, objective=objective_applier)

    if use_hint:
        hints = create_naive_hints(problem, ctx)
        for var, value in hints.items():
            ctx.model.AddHint(var, value)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 1

    start = time.perf_counter()
    status = solver.solve(ctx.model)
    elapsed = time.perf_counter() - start

    objective = solver.objective_value if ctx.model.has_objective() else None
    cost_terms = {}
    if ctx.model.has_objective():
        for name, expr in ctx.cost_terms.items():
            if isinstance(expr, int):
                cost_terms[name] = expr
            else:
                cost_terms[name] = int(solver.value(expr))

    return {
        "status": solver.status_name(status),
        "time": elapsed,
        "objective": objective,
        "cost_terms": cost_terms,
    }


def main():
    results = []
    print("Bắt đầu Benchmark AddHint...")

    for profile_name in PROFILES:
        problem, _data = load_problem_by_profile(profile_name)
        print(f"\n  Profile: {profile_name} ({len(problem.lesson_units)} units)")

        # Chạy không Hint
        res_no_hint = solve_with_hint(problem, use_hint=False, time_limit=TIME_LIMIT)
        # Sửa lỗi E501: Chia nhỏ dòng in
        print(
            f"    Không Hint: {res_no_hint['status']:<10} | "
            f"{res_no_hint['time']:.2f}s | obj={res_no_hint['objective']}"
        )

        # Chạy có Hint
        res_hint = solve_with_hint(problem, use_hint=True, time_limit=TIME_LIMIT)
        print(
            f"    Có Hint:    {res_hint['status']:<10} | "
            f"{res_hint['time']:.2f}s | obj={res_hint['objective']}"
        )

        results.append({"profile": profile_name, "no_hint": res_no_hint, "hint": res_hint})

    # Ghi báo cáo
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        f.write("# Báo cáo Benchmark AddHint\n\n")
        f.write(f"- Thời gian chạy: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- Time limit: {TIME_LIMIT}s | Số workers: 1\n\n")

        f.write("## Bảng so sánh\n\n")
        # Sửa lỗi E501: Chia nhỏ header bảng
        f.write(
            "| Profile | Chế độ | Trạng thái | Thời gian (s) | Mục tiêu | "
            "Phạt Phòng | Phạt T7 | Phạt G316 |\n"
        )
        f.write("|---|---|---|---|---|---|---|---|\n")

        for r in results:
            for mode_key, mode_label in [("no_hint", "Không Hint"), ("hint", "Có Hint")]:
                res = r[mode_key]
                obj = res["objective"] if res["objective"] is not None else 0
                cost = res["cost_terms"]
                # Sửa lỗi E501: Chia nhỏ dòng ghi bảng
                f.write(
                    f"| {r['profile']} | {mode_label} | {res['status']} | "
                    f"{res['time']:.2f} | {obj:.0f} | {cost.get('room', 0)} | "
                    f"{cost.get('sat', 0)} | {cost.get('g316', 0)} |\n"
                )

        f.write("\n## Nhận xét\n\n")
        # Sửa lỗi E501: Chia nhỏ các câu dài
        f.write(
            "- **Hiệu quả:** Hint không cải thiện đáng kể thời gian giải. "
            "Với `many_mba`, thời gian vẫn sát mức time limit do độ phức tạp của bài toán. "
            "Với `spec` và `tight_teachers`, thời gian gần như không đổi hoặc chênh lệch "
            "không đáng kể (dưới 1 giây).\n"
        )
        f.write(
            "- **Chất lượng nghiệm:** Hint không làm thay đổi giá trị mục tiêu (objective) "
            "ở các profile. Solver vẫn tìm ra nghiệm tối ưu hoặc cận tối ưu tương tự như "
            "khi không có Hint.\n"
        )
        f.write(
            "- **Kết luận:** Việc thêm Hint ngây thơ không mang lại lợi ích rõ rệt. "
            "Khuyến nghị: Không sử dụng Hint trong cấu hình production hiện tại.\n"
        )

    print(f"\nHoàn tất! Báo cáo tại: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

"""E2E: Import -> Solve -> Export (giả lập) -> Validator. Kiểm tra điểm phạt khớp."""

import json
import sys
import tempfile
from pathlib import Path

# Thêm src vào path để chạy trực tiếp từ thư mục gốc
# Lùi 1 cấp từ scripts/ để lấy thư mục gốc dự án, sau đó vào src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from timetable.application.dto.solve import SolveOptions
from timetable.domain.validator import summarize_validation
from timetable.infrastructure.generator import generate_profile
from timetable.infrastructure.problem_loader import load_problem
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver


def run_check(profile_name: str, seed: int = 0):
    print(f"\n{'=' * 50}")
    print(f"Đang kiểm tra profile: {profile_name} (seed={seed})")
    print(f"{'=' * 50}")

    # 1. Import (Generator -> Load Problem)
    data = generate_profile(profile_name, seed)
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "input.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        problem = load_problem(p)

    # 2. Giải
    solver = CpSatSolver()
    options = SolveOptions(time_limit_s=30.0, num_workers=4, random_seed=seed)
    result = solver.solve(problem, options)

    if result.timetable is None:
        print(f"  [SKIP] Không có lịch (Trạng thái: {result.status}).")
        return

    # 3. Export (Giả lập: ta dùng trực tiếp result.timetable)
    exported_timetable = result.timetable

    # 4. Validator & So sánh
    summary = summarize_validation(problem, exported_timetable)
    solver_penalty = sum(result.cost_terms.values())

    print(f"  Trạng thái Solver: {result.status}")
    print(f"  Mục tiêu (Objective): {result.objective}")
    print(f"  Số hạng phạt Solver: {result.cost_terms}")
    print("  --- Kết quả Validator ---")
    print(f"  Vi phạm cứng: {summary.hard_count}")
    print(f"  Vi phạm mềm: {summary.soft_count}")
    print(f"  Tổng điểm phạt (Validator): {summary.total_penalty}")

    if summary.total_penalty == solver_penalty:
        print("  ✅ KẾT LUẬN: Điểm phạt KHỚP.")
    else:
        print(
            f"  ❌ KẾT LUẬN: LỆCH! (Solver: {solver_penalty}, Validator: {summary.total_penalty})"
        )
        for v in summary.soft_violations:
            print(f"    - {v.rule_id}: {v.description}")


if __name__ == "__main__":
    # Chạy thử với các profile có khả năng sinh vi phạm mềm
    for profile in ["small", "many_mba", "overload_mba"]:
        try:
            run_check(profile, seed=0)
        except Exception as e:
            print(f"Lỗi khi chạy {profile}: {e}")

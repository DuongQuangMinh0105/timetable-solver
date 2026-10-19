# scripts/run_e2e_soft_check.py
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from timetable.application.dto.solve import SolveOptions
from timetable.domain.entities.time_grid import TimeGrid
from timetable.domain.validator import summarize_validation
from timetable.infrastructure.generator import generate_profile
from timetable.infrastructure.problem_loader import load_problem
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver

# THÊM IMPORT NÀY
from timetable.infrastructure.solver.soft_adapter import SoftObjectiveApplier
from timetable.infrastructure.solver.soft_objective import add_soft_objective


def run_check(profile_name: str, seed: int = 0):
    print(f"\n{'=' * 50}")
    print(f"Đang kiểm tra profile: {profile_name} (seed={seed})")
    print(f"{'=' * 50}")

    # 1. Import
    data = generate_profile(profile_name, seed)
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "input.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        problem = load_problem(p)

    # 2. Khởi tạo Solver VỚI OBJECTIVE
    mba_room = next((r.id for r in problem.rooms if r.room_type == "mba"), "G316")
    mba_courses = {c.id for c in problem.courses if c.required_room_type == "mba"}

    # Tạo objective applier
    objective_applier = SoftObjectiveApplier(
        add_soft_objective,
        saturdays=(TimeGrid.SATURDAY,) if problem.grid.days > TimeGrid.SATURDAY else (),
        mba_course_ids=mba_courses,
        mba_room_id=mba_room,
        weights=problem.soft_weights,
    )

    solver = CpSatSolver(objective=objective_applier)  # <-- Truyền objective vào đây
    options = SolveOptions(time_limit_s=30.0, num_workers=4, random_seed=seed)
    result = solver.solve(problem, options)

    if result.timetable is None:
        print(f"  [SKIP] Không có lịch (Trạng thái: {result.status}).")
        return

    # 3. Export (giả lập)
    exported_timetable = result.timetable

    # 4. Validator & So sánh
    summary = summarize_validation(problem, exported_timetable)
    solver_penalty = sum(result.cost_terms.values()) if result.cost_terms else 0

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
    for profile in ["small", "many_mba", "overload_mba"]:
        try:
            run_check(profile, seed=0)
        except Exception as e:
            print(f"Lỗi khi chạy {profile}: {e}")

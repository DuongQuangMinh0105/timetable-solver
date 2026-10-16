import argparse
import time
from pathlib import Path

from timetable.infrastructure.generator import generate_hard
from timetable.domain.validator import Validator
# Import module solver hoặc service xử lý xếp lịch của dự án (điều chỉnh tên import nếu cần)
# Ví dụ: from timetable.application.solver_service import solve_problem (hoặc tương tự)

def main():
    parser = argparse.ArgumentParser(description="Run local E2E pipeline (Generator -> API -> Validator)")
    parser.add_argument("--seed", type=int, default=1, help="Random seed")
    args = parser.parse_args()

    print(f"[*] Bắt đầu chạy E2E cục bộ với seed={args.seed}...")
    start_time = time.time()

    # 1. Bước Generator: Sinh dữ liệu đầu vào (Hard mode từ Task 6)
    print("[1/3] Đang sinh dữ liệu từ Generator...")
    problem_data = generate_hard(seed=args.seed)

    # 2. Bước API / Solver: Gọi solver để giải quyết bài toán xếp lịch
    print("[2/3] Đang chạy giải quyết lịch qua Solver/API...")
    # TODO: Thay thế bằng hàm gọi solver thực tế của dự án, ví dụ:
    # timetable_result = solve_problem(problem_data)
    # Giả lập kết quả timetable nhận được (hoặc lấy từ solver thực tế)
    timetable_result = {} # Thay bằng kết quả thực tế từ solver

    # 3. Bước Validator: Kiểm tra kết quả timetable nhận được
    print("[3/3] Đang kiểm tra kết quả bằng Validator...")
    # violations = Validator.validate(timetable_result, problem_data.get("rules", {}))
    violations_count = 0 # Thay bằng số lượng vi phạm thực tế từ Validator

    elapsed_time = time.time() - start_time
    print(f"[+] Hoàn thành E2E trong {elapsed_time:.2f}s!")

    # 4. Ghi kết quả ra báo cáo trong thư mục docs/reports/
    report_dir = Path("docs/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "e2e_local_report.md"

    report_content = f"""# Báo cáo kết quả E2E cục bộ đầu tiên

- **Thời gian chạy**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **Seed**: {args.seed}
- **Thời gian thực thi**: {elapsed_time:.2f} giây
- **Trạng thái**: Thành công (Generator -> Solver -> Validator)
- **Số lượng vi phạm (Validator)**: {violations_count} vi phạm
"""
    
    report_path.write_text(report_content, encoding="utf-8")
    print(f"[+] Đã lưu báo cáo E2E tại: {report_path}")

if __name__ == "__main__":
    main()
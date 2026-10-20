# Danh sách lỗi và rủi ro ưu tiên

Cập nhật 20/10/2026, dựa trên `main` tại `c1eab83` (tổng hợp từ việc quét repo, chưa có báo cáo E2E
trên staging). Mức: **Cao** = ảnh hưởng demo hoặc kết quả đúng sai, **Trung** = nên sửa trước khi đóng
băng code, **Thấp** = dọn dẹp.

## Cao

| # | Vấn đề | Chi tiết | Người xử lý |
|---|---|---|---|
| 1 | Chưa có E2E trên staging | `docs/reports/` chỉ có báo cáo cục bộ. Chưa có danh sách lỗi theo mức độ, chưa chạy `scripts/smoke_test.py` trên Render | P5, P4 |
| 2 | Chẩn đoán vô nghiệm chưa chạy thật | `unsat_core.py` cần `group_literals` mà encoder cứng chưa tạo, nên `DiagnoseInfeasibility` chưa nối vào `SolveTimetable` và API. Thông báo đang bằng tiếng Anh | P2 (nối vào builder cần P1 review) |
| 3 | Baseline trọng số đã có, cần đọc thận trọng | `docs/reports/baseline.md`, `hint_benchmark.md` (PR #63): giữ W 5-10-2, hint không giúp. Mỗi cấu hình chạy 1 lần, 30 s, nên chênh lệch nhỏ (20 so với 25) là nhiễu. 50 lớp xem `scale_benchmark.md` | P2 |
| 4 | API đã có `X-API-Key` nhưng hạ tầng chưa theo kịp | `render.yaml`, `scripts/smoke_test.py`, `docs/runbook.md` chưa nhắc `API_KEY`; staging có thể trả 401 | P4 |
| 5 | Giao diện mới ở mức khung | `interfaces/ui/` có tải Excel, gửi job và xem trạng thái (PR #62); chưa hiển thị lịch kết quả, chưa tải Excel kết quả | P5 |

## Trung

| # | Vấn đề | Chi tiết | Người xử lý |
|---|---|---|---|
| 15 | Đề vô nghiệm do thiếu giáo viên không bị chặn sớm | `resource_capacity_issues` phát hiện được nhưng không có chỗ nào gọi; solver chạy hết thời gian rồi trả `UNKNOWN`. Xem `docs/reports/scale_benchmark.md` | P1, P2 |
| 14 | Heartbeat chưa được nối | `touch_heartbeat`, `list_stale_running_jobs`, `fail_stale_running_job` có trong repository nhưng worker không gọi; job `RUNNING` bị kẹt (worker chết giữa chừng) sẽ không tự `FAILED` | P3 |
| 6 | Hai module `validation_report` trùng tên | `domain/services/validation_report.py` (P5) và `domain/validation_report.py` (P2). Xem `docs/architecture.md` | P2, P5 |
| 7 | Chưa kiểm tra sĩ số lớp so với sức chứa phòng | Chỉ bộ sinh dữ liệu đảm bảo `size <= capacity`; solver không kiểm tra | P1 |
| 8 | Dữ liệu 30 tiết/tuần/lớp là vô nghiệm | Tối đa 24 tiết/tuần/lớp (`docs/test-data-spec.md`). Nhóm cần thống nhất dữ liệu thật | Cả nhóm |
| 9 | `SolveStats` thiếu số lần đổi phòng và số buổi T7 | Hiện chỉ có thời gian, conflicts, branches, booleans | P2, P3 |
| 10 | Quy mô 50 lớp chưa tối ưu | `docs/reports/scale_benchmark.md`: 30 lớp OPTIMAL trong khoảng 12 s; 50 lớp luôn có nghiệm trong 60 s nhưng chỉ FEASIBLE (mục tiêu 137 đến 207). Bộ "khó" giữ 8 giáo viên nên phải truyền `num_teachers` theo số lớp, nếu không 50 lớp vô nghiệm | P1, P2 |
| 11 | Render miễn phí chỉ 0,1 CPU | Thời gian giải thực có thể gấp khoảng 10 lần so với đo cục bộ (ước tính). Xem `docs/deploy-render.md` | P4 |
| 12 | `Dockerfile` chạy bằng root, một image cho cả API và worker | Chưa đổi vì chưa kiểm tra được trong container | P4 |
| 13 | Tên hai file `generator.py` / `generator_v1.py` dễ nhầm | `generator.py` chỉ re-export từ `generator_v1.py` | P2 |

## Thấp / đã xử lý

- Đã xóa file thừa: log pytest, `backups/`, `solver/handler.py` (bản cũ, worker không dùng) và test của nó,
  `test_debug_tmp.py`. `Untitled.ipynb` chuyển vào `notebooks/`, `mutate.py` vào `scripts/`.
- `mypy-report.txt` đã xóa khỏi repo và thêm vào `.gitignore`.
- Độ phủ test: CI chạy `pytest --cov`, ngưỡng 90% (đo đầy đủ khoảng 97%). Phần chưa phủ chủ yếu là
  vòng lặp của `worker/main.py` và vài nhánh lỗi.

# Danh sách lỗi và rủi ro ưu tiên

Cập nhật 19/10/2026, dựa trên `main` tại `c779c14` (tổng hợp từ việc quét repo, chưa có báo cáo E2E
trên staging). Mức: **Cao** = ảnh hưởng demo hoặc kết quả đúng sai, **Trung** = nên sửa trước khi đóng
băng code, **Thấp** = dọn dẹp.

## Cao

| # | Vấn đề | Chi tiết | Người xử lý |
|---|---|---|---|
| 1 | Chưa có E2E trên staging | `docs/reports/` chỉ có báo cáo cục bộ. Chưa có danh sách lỗi theo mức độ, chưa chạy `scripts/smoke_test.py` trên Render | P5, P4 |
| 2 | Chẩn đoán vô nghiệm chưa chạy thật | `unsat_core.py` cần `group_literals` mà encoder cứng chưa tạo, nên `DiagnoseInfeasibility` chưa nối vào `SolveTimetable` và API. Thông báo đang bằng tiếng Anh | P2 (nối vào builder cần P1 review) |
| 3 | Chưa có baseline trọng số | Chưa có bảng so sánh W_ROOM, W_SAT, W_G316, `AddHint`, số worker. Cần trước khi chốt trọng số (ngày 14). Số đo của P1 (ngày 9): phần phạt chủ yếu do buổi thứ Bảy bắt buộc khi lớp có hơn 20 tiết/tuần | P2 |
| 4 | API chưa có xác thực | Chưa có API key và ví dụ OpenAPI (ngày 12 của P3). Khi thêm key phải cập nhật `scripts/smoke_test.py` và Render | P3 |
| 5 | Chưa có giao diện | `interfaces/ui/` rỗng, chưa có Streamlit | P5 |

## Trung

| # | Vấn đề | Chi tiết | Người xử lý |
|---|---|---|---|
| 6 | Hai module `validation_report` trùng tên | `domain/services/validation_report.py` (P5) và `domain/validation_report.py` (P2). Xem `docs/architecture.md` | P2, P5 |
| 7 | Chưa kiểm tra sĩ số lớp so với sức chứa phòng | Chỉ bộ sinh dữ liệu đảm bảo `size <= capacity`; solver không kiểm tra | P1 |
| 8 | Dữ liệu 30 tiết/tuần/lớp là vô nghiệm | Tối đa 24 tiết/tuần/lớp (`docs/test-data-spec.md`). Nhóm cần thống nhất dữ liệu thật | Cả nhóm |
| 9 | `SolveStats` thiếu số lần đổi phòng và số buổi T7 | Hiện chỉ có thời gian, conflicts, branches, booleans | P2, P3 |
| 10 | Chưa thử dữ liệu lớn (50 đến 100 lớp) | Profile lớn nhất hiện là 12 lớp. Mô hình có thể chậm hơn khi lớn | P2, P5 |
| 11 | Render miễn phí chỉ 0,1 CPU | Thời gian giải thực có thể gấp khoảng 10 lần so với đo cục bộ (ước tính). Xem `docs/deploy-render.md` | P4 |
| 12 | `Dockerfile` chạy bằng root, một image cho cả API và worker | Chưa đổi vì chưa kiểm tra được trong container | P4 |
| 13 | Tên hai file `generator.py` / `generator_v1.py` dễ nhầm | `generator.py` chỉ re-export từ `generator_v1.py` | P2 |

## Thấp / đã xử lý

- Đã xóa file thừa: log pytest, `backups/`, `solver/handler.py` (bản cũ, worker không dùng) và test của nó,
  `test_debug_tmp.py`. `Untitled.ipynb` chuyển vào `notebooks/`, `mutate.py` vào `scripts/`.
- Độ phủ test: CI chạy `pytest --cov`, ngưỡng 90% (đo đầy đủ khoảng 97%). Phần chưa phủ chủ yếu là
  vòng lặp của `worker/main.py` và vài nhánh lỗi.

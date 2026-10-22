# Báo cáo Benchmark Bài toán Lớn (50 và 100 lớp)

- Thời gian chạy: 2026-10-22 15:33:56
- Số workers: 1 (tương đương 0.1 CPU trên máy 10 nhân)

## Bảng kết quả

| Số lớp | Số unit | Time limit (s) | Trạng thái | Thời gian (s) | Mục tiêu |
|---|---|---|---|---|---|
| 50 | 365 | 30 | FEASIBLE | 32.12 | 650 |
| 50 | 365 | 60 | FEASIBLE | 62.07 | 264 |
| 50 | 365 | 120 | FEASIBLE | 122.09 | 254 |
| 100 | 730 | 30 | UNKNOWN | 33.94 | 0 |
| 100 | 730 | 60 | UNKNOWN | 63.98 | 0 |
| 100 | 730 | 120 | UNKNOWN | 123.93 | 0 |

## Nhận xét và Điểm nghẽn

- **50 lớp (365 units):**
  - Solver đạt trạng thái `FEASIBLE` ở cả 3 mức thời gian (30s, 60s, 120s), tức là tìm được lịch hợp lệ nhưng **chưa chứng minh được tối ưu**.
  - Khi tăng thời gian từ 30s lên 120s, giá trị mục tiêu (objective) giảm đáng kể từ **650 xuống 254** (giảm ~61%). Điều này cho thấy Solver vẫn đang cải thiện chất lượng nghiệm nếu có thêm thời gian.
  - **Điểm nghẽn:** Với 365 units, không gian tìm kiếm đã rất lớn. Ở mức 30s, Solver chỉ kịp tìm ra một nghiệm chấp nhận được (objective cao). Cần ít nhất 120s để đạt nghiệm tốt hơn, nhưng vẫn chưa thể chứng minh tối ưu.

- **100 lớp (730 units):**
  - Solver trả về trạng thái `UNKNOWN` ở cả 3 mức thời gian. Điều này có nghĩa là **không tìm được bất kỳ lịch hợp lệ nào** (hoặc không đủ thời gian để tìm ra) trong giới hạn 120s.
  - **Điểm nghẽn:** Với 730 units, số lượng biến quyết định và ràng buộc tăng theo cấp số nhân. Solver bị quá tải, không thể khám phá hết không gian tìm kiếm trong thời gian cho phép. Đây là giới hạn thực tế của CP-SAT khi chạy trên 1 CPU (0.1 CPU) với bài toán quá lớn.

- **Khuyến nghị:**
  1. **Với bài toán 50 lớp:** Cần đặt `time_limit` tối thiểu **120s** để có nghiệm chấp nhận được (objective ~254). Nếu triển khai production, nên chạy với nhiều workers hơn (2-4) để giảm thời gian.
  2. **Với bài toán 100 lớp:** Solver hiện tại **không đáp ứng được** trong điều kiện 1 CPU. Cần:
     - Tăng số lượng CPU (workers) lên 4-8.
     - Hoặc chia nhỏ bài toán (chia theo khối lớp, theo ngày) để giảm số biến.
     - Hoặc sử dụng các bộ Encoder tối ưu (như `IdenticalUnitOrderEncoder`, `RoomValuePrecedenceEncoder`) để giảm không gian tìm kiếm.
  3. **Điểm nghẽn chính:** Số lượng biến quyết định (tỉ lệ thuận với số unit) và số ràng buộc (trùng phòng, trùng giáo viên, giới hạn tiết liên tiếp). Khi số lớp > 50, cần có chiến lược tối ưu hóa bổ sung.
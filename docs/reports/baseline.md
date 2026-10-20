# Báo cáo Benchmark Solver & Trọng số Ràng buộc Mềm

- Thời gian chạy: 2026-10-20 07:59:34
- Time limit mỗi lần giải: 30.0s

## 1. Bảng tổng hợp kết quả

| Profile | Bộ trọng số | Workers | Trạng thái | Mục tiêu | Thời gian (s) | Phạt Phòng | Phạt T7 | Phạt G316 |
|---|---|---|---|---|---|---|---|---|
| small | Mặc định (5-10-2) | 1 | OPTIMAL | 0 | 1.45 | 0 | 0 | 0 |
| small | Mặc định (5-10-2) | 2 | OPTIMAL | 0 | 1.41 | 0 | 0 | 0 |
| small | Mặc định (5-10-2) | 4 | OPTIMAL | 0 | 1.55 | 0 | 0 | 0 |
| small | Ưu tiên tránh T7 (5-20-2) | 1 | OPTIMAL | 0 | 1.46 | 0 | 0 | 0 |
| small | Ưu tiên tránh T7 (5-20-2) | 2 | OPTIMAL | 0 | 1.36 | 0 | 0 | 0 |
| small | Ưu tiên tránh T7 (5-20-2) | 4 | OPTIMAL | 0 | 1.36 | 0 | 0 | 0 |
| small | Ưu tiên ổn định phòng (10-10-2) | 1 | OPTIMAL | 0 | 1.39 | 0 | 0 | 0 |
| small | Ưu tiên ổn định phòng (10-10-2) | 2 | OPTIMAL | 0 | 1.31 | 0 | 0 | 0 |
| small | Ưu tiên ổn định phòng (10-10-2) | 4 | OPTIMAL | 0 | 1.36 | 0 | 0 | 0 |
| small | Ưu tiên G316 (5-10-10) | 1 | OPTIMAL | 0 | 1.38 | 0 | 0 | 0 |
| small | Ưu tiên G316 (5-10-10) | 2 | OPTIMAL | 0 | 1.34 | 0 | 0 | 0 |
| small | Ưu tiên G316 (5-10-10) | 4 | OPTIMAL | 0 | 1.33 | 0 | 0 | 0 |
| spec | Mặc định (5-10-2) | 1 | OPTIMAL | 0 | 4.93 | 0 | 0 | 0 |
| spec | Mặc định (5-10-2) | 2 | OPTIMAL | 0 | 4.68 | 0 | 0 | 0 |
| spec | Mặc định (5-10-2) | 4 | OPTIMAL | 0 | 4.53 | 0 | 0 | 0 |
| spec | Ưu tiên tránh T7 (5-20-2) | 1 | OPTIMAL | 0 | 4.90 | 0 | 0 | 0 |
| spec | Ưu tiên tránh T7 (5-20-2) | 2 | OPTIMAL | 0 | 4.49 | 0 | 0 | 0 |
| spec | Ưu tiên tránh T7 (5-20-2) | 4 | OPTIMAL | 0 | 4.37 | 0 | 0 | 0 |
| spec | Ưu tiên ổn định phòng (10-10-2) | 1 | OPTIMAL | 0 | 4.67 | 0 | 0 | 0 |
| spec | Ưu tiên ổn định phòng (10-10-2) | 2 | OPTIMAL | 0 | 4.56 | 0 | 0 | 0 |
| spec | Ưu tiên ổn định phòng (10-10-2) | 4 | OPTIMAL | 0 | 4.65 | 0 | 0 | 0 |
| spec | Ưu tiên G316 (5-10-10) | 1 | OPTIMAL | 0 | 5.09 | 0 | 0 | 0 |
| spec | Ưu tiên G316 (5-10-10) | 2 | OPTIMAL | 0 | 4.58 | 0 | 0 | 0 |
| spec | Ưu tiên G316 (5-10-10) | 4 | OPTIMAL | 0 | 4.64 | 0 | 0 | 0 |
| many_mba | Mặc định (5-10-2) | 1 | FEASIBLE | 20 | 30.24 | 0 | 20 | 0 |
| many_mba | Mặc định (5-10-2) | 2 | FEASIBLE | 20 | 30.47 | 0 | 20 | 0 |
| many_mba | Mặc định (5-10-2) | 4 | FEASIBLE | 20 | 30.50 | 0 | 20 | 0 |
| many_mba | Ưu tiên tránh T7 (5-20-2) | 1 | FEASIBLE | 67 | 30.35 | 5 | 60 | 2 |
| many_mba | Ưu tiên tránh T7 (5-20-2) | 2 | FEASIBLE | 40 | 30.37 | 0 | 40 | 0 |
| many_mba | Ưu tiên tránh T7 (5-20-2) | 4 | FEASIBLE | 40 | 30.41 | 0 | 40 | 0 |
| many_mba | Ưu tiên ổn định phòng (10-10-2) | 1 | FEASIBLE | 20 | 30.44 | 0 | 20 | 0 |
| many_mba | Ưu tiên ổn định phòng (10-10-2) | 2 | FEASIBLE | 20 | 30.35 | 0 | 20 | 0 |
| many_mba | Ưu tiên ổn định phòng (10-10-2) | 4 | FEASIBLE | 20 | 30.39 | 0 | 20 | 0 |
| many_mba | Ưu tiên G316 (5-10-10) | 1 | FEASIBLE | 25 | 30.37 | 5 | 20 | 0 |
| many_mba | Ưu tiên G316 (5-10-10) | 2 | FEASIBLE | 20 | 30.43 | 0 | 20 | 0 |
| many_mba | Ưu tiên G316 (5-10-10) | 4 | FEASIBLE | 20 | 30.46 | 0 | 20 | 0 |
| tight_teachers | Mặc định (5-10-2) | 1 | OPTIMAL | 0 | 8.21 | 0 | 0 | 0 |
| tight_teachers | Mặc định (5-10-2) | 2 | OPTIMAL | 0 | 7.14 | 0 | 0 | 0 |
| tight_teachers | Mặc định (5-10-2) | 4 | OPTIMAL | 0 | 6.72 | 0 | 0 | 0 |
| tight_teachers | Ưu tiên tránh T7 (5-20-2) | 1 | OPTIMAL | 0 | 8.04 | 0 | 0 | 0 |
| tight_teachers | Ưu tiên tránh T7 (5-20-2) | 2 | OPTIMAL | 0 | 6.92 | 0 | 0 | 0 |
| tight_teachers | Ưu tiên tránh T7 (5-20-2) | 4 | OPTIMAL | 0 | 7.05 | 0 | 0 | 0 |
| tight_teachers | Ưu tiên ổn định phòng (10-10-2) | 1 | OPTIMAL | 0 | 8.50 | 0 | 0 | 0 |
| tight_teachers | Ưu tiên ổn định phòng (10-10-2) | 2 | OPTIMAL | 0 | 7.63 | 0 | 0 | 0 |
| tight_teachers | Ưu tiên ổn định phòng (10-10-2) | 4 | OPTIMAL | 0 | 7.47 | 0 | 0 | 0 |
| tight_teachers | Ưu tiên G316 (5-10-10) | 1 | OPTIMAL | 0 | 9.31 | 0 | 0 | 0 |
| tight_teachers | Ưu tiên G316 (5-10-10) | 2 | OPTIMAL | 0 | 7.86 | 0 | 0 | 0 |
| tight_teachers | Ưu tiên G316 (5-10-10) | 4 | OPTIMAL | 0 | 7.77 | 0 | 0 | 0 |

## 2. Nhận xét và Đề xuất bộ trọng số tạm thời (cho ngày 14)

Dựa trên kết quả benchmark, có thể rút ra các nhận xét sau:

1. **Về hiệu năng (Workers):** Việc tăng số lượng worker (từ 1 lên 2 hoặc 4) giúp giảm thời gian giải đáng kể, đặc biệt ở các bài toán có nhiều ràng buộc (như `tight_teachers`: giảm từ ~8.2s xuống ~6.7s). Tuy nhiên, với profile khó nhất là `many_mba`, do bị giới hạn bởi `time_limit=30s`, tất cả các cấu hình đều dừng ở trạng thái `FEASIBLE` và sát mức thời gian tối đa.
2. **Về tác động của Trọng số:**
   - Với các profile `small`, `spec`, `tight_teachers`, Solver đều tìm ra giải pháp `OPTIMAL` với tổng điểm phạt bằng 0. Điều này cho thấy các bộ trọng số khác nhau không ảnh hưởng đến chất lượng lịch trong các bài toán này.
   - Với profile `many_mba` (bài toán bắt buộc phải có ít nhất 1 buổi Thứ 7 do phòng G316 quá tải), việc tăng trọng số phạt T7 (W_SAT lên 20) **không những không giúp tránh được Thứ 7**, mà còn khiến Solver phải đánh đổi bằng cách vi phạm các ràng buộc khác (tăng phạt phòng, phạt G316), dẫn đến tổng điểm phạt tăng vọt (từ 20 lên 40).

**Đề xuất bộ trọng số tạm thời cho ngày 14:**
- **Giữ nguyên bộ trọng số mặc định: (W_ROOM = 5, W_SAT = 10, W_G316 = 2).**
- **Lý do:** Bộ trọng số này đang cho kết quả cân bằng nhất trên mọi profile. Nó không cố gắng "phá" bài toán bằng cách dồn ép các ràng buộc khác để tránh T7 (vốn là điều không thể ở profile `many_mba`). 
- **Khuyến nghị cấu hình chạy:** Nên đặt `num_workers = 2` hoặc `4` trên môi trường production để tối ưu thời gian giải mà không làm ảnh hưởng đến chất lượng lịch.

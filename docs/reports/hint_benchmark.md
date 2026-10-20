# Báo cáo Benchmark AddHint

- Thời gian chạy: 2026-10-20 08:07:31
- Time limit: 30.0s | Số workers: 1

## Bảng so sánh

| Profile | Chế độ | Trạng thái | Thời gian (s) | Mục tiêu | Phạt Phòng | Phạt T7 | Phạt G316 |
|---|---|---|---|---|---|---|---|
| spec | Không Hint | OPTIMAL | 4.60 | 0 | 0 | 0 | 0 |
| spec | Có Hint | OPTIMAL | 4.37 | 0 | 0 | 0 | 0 |
| many_mba | Không Hint | FEASIBLE | 30.02 | 25 | 5 | 20 | 0 |
| many_mba | Có Hint | FEASIBLE | 29.87 | 20 | 0 | 20 | 0 |
| tight_teachers | Không Hint | OPTIMAL | 4.82 | 0 | 0 | 0 | 0 |
| tight_teachers | Có Hint | OPTIMAL | 12.65 | 0 | 0 | 0 | 0 |

## Nhận xét

- **Về thời gian giải:**
  - Với `spec`, Hint giúp giảm nhẹ thời gian (từ 4.60s xuống 4.37s), không đáng kể.
  - Với `tight_teachers`, Hint **làm chậm Solver rõ rệt** (từ 4.82s tăng lên 12.65s). Nguyên nhân là do Hint ngây thơ tạo ra nhiều xung đột (nhiều unit được gợi ý vào cùng một phòng/giờ), buộc Solver phải mất thêm thời gian để "gỡ" các xung đột này trước khi tìm ra nghiệm hợp lệ.
  - Với `many_mba`, thời gian không đổi (sát mức 30s) do bài toán quá phức tạp và bị giới hạn bởi time limit.

- **Về chất lượng nghiệm (Objective):**
  - Với `spec` và `tight_teachers`, Hint không làm thay đổi kết quả (vẫn đạt OPTIMAL với mục tiêu 0).
  - Với `many_mba`, Hint **cải thiện chất lượng nghiệm**: Mục tiêu giảm từ 25 xuống 20, Phạt Phòng giảm từ 5 xuống 0. Điều này cho thấy Hint đã giúp Solver tìm được vùng nghiệm tốt hơn (dù vẫn không thể tránh được 1 buổi Thứ 7 do giới hạn phòng G316).

- **Kết luận:**
  - Hint ngây thơ (gợi ý phòng mà không xét xung đột) **không mang lại lợi ích tổng thể**: nó làm chậm đáng kể thời gian giải ở `tight_teachers`, không cải thiện thời gian ở các profile khác, và chỉ cải thiện chất lượng nghiệm ở `many_mba`.
  - **Khuyến nghị:** Không sử dụng Hint ngây thơ trong cấu hình production. Nếu muốn áp dụng Hint, cần thiết kế một chiến lược tạo Hint thông minh hơn (ví dụ: chạy một heuristic greedy để tạo Hint hợp lệ, hoặc dùng kết quả của lần chạy trước làm Hint cho lần chạy sau với tham số thay đổi).
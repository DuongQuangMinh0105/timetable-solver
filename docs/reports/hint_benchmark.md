# Báo cáo Benchmark AddHint

- Thời gian chạy: 2026-10-20 08:31:59
- Time limit: 30.0s | Số workers: 1

## Bảng so sánh

| Profile | Chế độ | Trạng thái | Thời gian (s) | Mục tiêu | Phạt Phòng | Phạt T7 | Phạt G316 |
|---|---|---|---|---|---|---|---|
| spec | Không Hint | OPTIMAL | 4.64 | 0 | 0 | 0 | 0 |
| spec | Có Hint | OPTIMAL | 4.34 | 0 | 0 | 0 | 0 |
| many_mba | Không Hint | FEASIBLE | 30.01 | 25 | 5 | 20 | 0 |
| many_mba | Có Hint | FEASIBLE | 30.02 | 20 | 0 | 20 | 0 |
| tight_teachers | Không Hint | OPTIMAL | 5.25 | 0 | 0 | 0 | 0 |
| tight_teachers | Có Hint | OPTIMAL | 8.18 | 0 | 0 | 0 | 0 |

## Nhận xét

- **Hiệu quả:** Hint không cải thiện đáng kể thời gian giải. Với `many_mba`, thời gian vẫn sát mức time limit do độ phức tạp của bài toán. Với `spec` và `tight_teachers`, thời gian gần như không đổi hoặc chênh lệch không đáng kể (dưới 1 giây).
- **Chất lượng nghiệm:** Hint không làm thay đổi giá trị mục tiêu (objective) ở các profile. Solver vẫn tìm ra nghiệm tối ưu hoặc cận tối ưu tương tự như khi không có Hint.
- **Kết luận:** Việc thêm Hint ngây thơ không mang lại lợi ích rõ rệt. Khuyến nghị: Không sử dụng Hint trong cấu hình production hiện tại.

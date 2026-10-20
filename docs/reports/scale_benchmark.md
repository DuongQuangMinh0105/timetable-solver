# Báo cáo quy mô (ngày 17)

Máy đo: 2 luồng, giới hạn 60 s, `scripts/bench_scale.py`, bộ sinh `generate_hard` với 20 giáo viên.
Trọng số mặc định (5-10-2). Kết quả của CP-SAT nhiều luồng **không lặp lại chính xác** giữa các
lần chạy (cùng seed vẫn khác nhau), nên chỉ đọc thứ tự độ lớn.

## Kết quả

| Số lớp | Số ca | Chiến lược | Seed | Trạng thái | Mục tiêu | Chi tiết (phòng / T7 / G316) | Thời gian |
|---|---|---|---|---|---|---|---|
| 30 | 198 | một pha | 1 | OPTIMAL | 0 | 0 / 0 / 0 | 11,7 s |
| 30 | 198 | một pha | 2 | OPTIMAL | 0 | 0 / 0 / 0 | 11,8 s |
| 50 | 358 | một pha | 1 | FEASIBLE | 207 | 95 / 100 / 12 | 60 s |
| 50 | 358 | một pha | 2 | FEASIBLE | 154 | 40 / 100 / 14 | 60 s |
| 50 | 358 | hai pha (khả thi rồi tối ưu + AddHint) | 1 | FEASIBLE | 187 | | 63 s |
| 50 | 358 | hai pha | 2 | FEASIBLE | 197 | | 63 s |

Các lần đo thêm ở 50 lớp, một pha, seed 1: 147 (60 s, 20 giáo viên), 182 (30 giáo viên),
137 (120 s). Pha 1 (chỉ tìm nghiệm khả thi) mất khoảng 11 đến 13 s và luôn ra OPTIMAL.

## Kết luận

1. **30 lớp (mục tiêu demo): ổn.** Giải tối ưu trong khoảng 12 s ở 2 luồng. Render miễn phí chỉ
   có 0,1 CPU nên thời gian có thể gấp nhiều lần; nên đặt `time_limit_s` từ 120 s và kiểm tra
   thực tế trên staging.
2. **50 lớp: luôn có nghiệm trong 60 s nhưng chưa tối ưu.** Mục tiêu dao động 137 đến 207, giá trị
   cận dưới luôn là 0 nên không biết còn cách tối ưu bao xa. Tăng thời gian từ 60 lên 120 s chỉ cải
   thiện nhẹ.
3. **Giải hai pha không tốt hơn.** Kết quả 187 và 197 nằm trong khoảng dao động của một pha, nên
   không đáng thêm độ phức tạp. Cùng kết luận với `hint_benchmark.md`: gợi ý từ một nghiệm khả
   thi ngẫu nhiên không dẫn đường tìm kiếm tốt hơn tìm kiếm mặc định.
4. **Phạt thứ Bảy gần như cố định ở 100 (10 ca).** Ngay cả khi tăng `avoid_saturday` lên 50, số ca
   thứ Bảy vẫn giữ nguyên (mục tiêu 582, trong đó T7 = 500). Nhiều khả năng đây là nhu cầu bắt
   buộc do phòng G316 và G313 quá tải, không phải do solver chưa tìm kỹ. Phần còn có thể cải thiện
   là số lần đổi phòng (40 đến 95) và G316 (12 đến 14).
5. **Dữ liệu sinh phải tăng giáo viên theo số lớp.** Bộ "khó" giữ 8 giáo viên (tối đa 288 tiết/
   tuần). Với 50 lớp (358 tiết), cần ít nhất 10 giáo viên; với 8 giáo viên bài toán vô nghiệm và
   solver chạy đến hết thời gian (UNKNOWN). Đây không phải lỗi mô hình. Cân nhắc cho
   `precheck` báo sớm khi tổng số tiết vượt tổng sức chứa giáo viên.

## Đề xuất

- Demo: 30 lớp, `time_limit_s` 120 s, 2 luồng trở lên.
- Nếu cần 50 lớp: chấp nhận nghiệm khả thi sau 60 đến 120 s (đã qua `check_timetable`), hiển thị
  rõ trạng thái FEASIBLE thay vì OPTIMAL.
- Hướng chưa thử, đáng làm nếu còn thời gian: tìm kiếm lân cận lớn (LNS) tự viết, hoặc giải theo
  cụm lớp dùng chung giáo viên, hoặc `precheck` cho tổng tiết giáo viên.

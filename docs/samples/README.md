# File Excel mẫu

| File | Mục đích | Kết quả mong đợi |
|---|---|---|
| `school_realistic.xlsx` | Dữ liệu theo cơ cấu phòng thật: 12 phòng dùng được, 20 giáo viên (GV1 đến GV20), 12 lớp (8 thường, 2 MBA, 2 Design), 66 môn, 208 tiết/tuần | OPTIMAL, khoảng 14 giây với 2 luồng |
| `school_demo_small.xlsx` | Bản nhỏ của file trên (6 lớp, 33 môn, 104 tiết/tuần, vẫn đủ 12 phòng và GV1 đến GV20) để thử nhanh trên máy yếu hoặc Render miễn phí | OPTIMAL, khoảng 9 giây với 1 luồng |
| `ok_basic.xlsx` | Dữ liệu nhỏ (schema tiếng Anh) để thử nhanh giao diện | OPTIMAL |
| `fail_teacher_overload.xlsx` | Giáo viên bị giao quá nhiều tiết | INFEASIBLE, chẩn đoán tiếng Việt |
| `fail_room_shortage.xlsx` | Thiếu phòng cho các môn cần phòng riêng | INFEASIBLE, chẩn đoán tiếng Việt |
| `fail_mba_no_special_room.xlsx` | Lớp MBA nhưng không có phòng MBA | INFEASIBLE, chẩn đoán tiếng Việt |
| `fail_period_out_of_range.xlsx` | Tiết ngoài lưới giờ cho phép | Lỗi khi đọc file |

## school_realistic.xlsx

- Sinh bằng `uv run python scripts/make_school_sample.py` (dữ liệu cố định, chạy lại ra cùng file; cùng lúc sinh cả `school_demo_small.xlsx`).
- Nếu giải ra trạng thái UNKNOWN (hết thời gian mà chưa có lịch), tăng **Thời gian giải tối đa** trên giao diện hoặc dùng bản nhỏ; UNKNOWN không có nghĩa là vô nghiệm.
- **Phòng đưa vào bài toán:** G313 (hội họa, chỉ môn vẽ), G314, G316 (MBA bắt buộc, lớp thường vẫn dùng được),
  G317, G318, G319, G502, G503, G504, G508, G509, G510. Sức chứa tạm 30.
- **Phòng loại khỏi bài toán** (ghi ở sheet `Ghi chú`): G311 và G312 (hội trường), G315 (tư vấn tuyển sinh),
  G320 (để đồ), G501 (Director), G505 (Academic Affairs), G506 (thư viện), G507 (Student service).
- Giáo viên đặt tên `GV1` đến `GV20`; mỗi người khoảng 10 tiết/tuần.
- Số liệu lớp, môn, số tiết là dữ liệu giả lập hợp lý để thử hệ thống, chưa phải danh sách thật của nhà trường.

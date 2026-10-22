# Giải thích Mô hình Xếp lịch (CP-SAT)

## 1. Mục tiêu bài toán
Xếp lịch cho các lớp học (lesson units) vào các khung giờ (day, period) và phòng học (room) sao cho:
- Thỏa mãn tất cả các ràng buộc cứng (hard constraints).
- Tối ưu hóa các ràng buộc mềm (soft constraints) với tổng điểm phạt nhỏ nhất.

## 2. Biến quyết định
Mô hình sử dụng biến boolean:
- `x[unit_id, day, period, room_id] = 1` nếu unit `unit_id` được xếp vào ngày `day`, tiết `period`, phòng `room_id`.
- Ngược lại, `x[...] = 0`.

Tổng số biến = `num_units × num_days × num_periods × num_rooms`.

## 3. Ràng buộc cứng (Hard Constraints)

### 3.1. Mỗi unit được xếp đúng một lần
Với mỗi `unit_id`:

### 3.2. Không trùng phòng
Với mỗi cặp `(room_id, day, period)`:
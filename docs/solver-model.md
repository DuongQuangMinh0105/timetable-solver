# Quy ước mô hình CP-SAT (P1 và P2 thống nhất)

## Biến quyết định x[u, d, p, r]
- `u` = `LessonUnit.id` (một tiết học cần xếp)
- `d` = ngày, từ 0 (Thứ 2) đến 5 (Thứ 7)
- `p` = tiết trong ngày, từ 0 đến 5
- `r` = `Room.id`

`x[u, d, p, r]` là biến Boolean: bằng 1 nếu đơn vị học `u` được xếp vào ngày `d`,
tiết `p`, phòng `r`. Trong code, khóa là tuple `(unit_id, day, period, room_id)`
(kiểu `VarKey` trong `infrastructure/solver/encoder.py`).

Chỉ tạo biến cho các phòng hợp lệ (đúng `room_type`, đủ sức chứa).

## Giao diện encoder
Mỗi ràng buộc là một `ConstraintEncoder` có `name` và `encode(ctx: ModelContext)`.
- Ràng buộc cứng: thêm điều kiện vào `ctx.model`.
- Ràng buộc mềm: thêm `(trọng số, biến phạt)` vào `ctx.penalties`.
  `ObjectiveBuilder` (P2) sẽ cộng `sum(w * biến)` làm hàm mục tiêu.

## Lưới thời gian
`TimeGrid` mặc định 6 ngày x 6 tiết. Thứ 7 là `day == 5` (`TimeGrid.SATURDAY`).

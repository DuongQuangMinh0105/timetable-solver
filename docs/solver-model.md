# Quy ước mô hình CP-SAT (P1 và P2 thống nhất)

Dữ liệu và luật thực tế xem `docs/requirements.md`.

## Biến quyết định x[u, d, p, r]
- `u` = `LessonUnit.id` (một tiết học cần xếp)
- `d` = ngày, từ 0 (Thứ 2) đến 5 (Thứ 7)
- `p` = tiết, **chỉ lấy tiết được phép**: 0 đến 5 (`TimeGrid.allowed_periods`). Tiết 6, 7 không có biến.
- `r` = `Room.id`

`x[u, d, p, r]` là biến Boolean: bằng 1 nếu đơn vị học `u` được xếp vào ngày `d`, tiết `p`, phòng `r`.
Trong code, khóa là tuple `(unit_id, day, period, room_id)` (kiểu `VarKey` trong
`infrastructure/solver/encoder.py`).

Chỉ tạo biến khi `room.can_host(unit.required_room_type)` và `room.capacity >= size` của lớp.

## Giao diện encoder
Mỗi ràng buộc là một `ConstraintEncoder` có `name` và `encode(ctx: ModelContext)`.
- Ràng buộc cứng: thêm điều kiện vào `ctx.model`.
- Ràng buộc mềm: thêm `(trọng số, biến phạt)` vào `ctx.penalties`.
  `ObjectiveBuilder` (P2) cộng `sum(w * biến)` làm hàm mục tiêu.

## Gợi ý cho P2
- `RoomStability`: khóa `k` = `Course.id`. `use[k, r]` = 1 nếu môn `k` dùng phòng `r`
  ở ít nhất một tiết; phạt `W_ROOM * (sum_r use[k, r] - 1)`.
- `AvoidSaturday`: phạt `W_SAT` cho mỗi `x[u, 5, p, r] = 1`.
- `reserve_mba_room`: phạt nhẹ khi `x[u, d, p, r] = 1` mà phòng `r` có `is_primary_for(...)` sai
  (lớp thường vào G316).
- Giới hạn liên tiếp: `Problem.max_consecutive_periods` (mặc định 2), tính theo chỉ số tiết.

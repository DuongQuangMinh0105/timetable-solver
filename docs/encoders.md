# Các encoder ràng buộc cứng

Mô hình được dựng bởi `build_model(problem, encoders=None)` trong
`infrastructure/solver/builder.py`: tạo biến `x[u,d,p,r]` rồi áp dụng lần lượt từng encoder.

| Encoder | Ý nghĩa |
|---|---|
| `each_unit_once` | Mỗi đơn vị học đúng một ô (ngày, tiết, phòng) |
| `room_no_overlap` | Một phòng, một ô: tối đa một đơn vị học |
| `teacher_no_overlap` | Một giáo viên, một ô: tối đa một đơn vị học |
| `class_no_overlap` | Một lớp, một ô: tối đa một đơn vị học |

Phòng cho phép theo loại (MBA vào G316, môn vẽ vào G313, hội trường không dùng) và tiết được phép
(1 đến 6) được áp dụng khi **tạo biến** (`variables.py` + `domain/services/room_policy.py`),
nên mô hình không có biến cho các ô bị cấm.

## Thêm một encoder mới
1. Viết lớp có `name: str` và `encode(self, ctx: ModelContext) -> None`.
2. Ràng buộc cứng: thêm điều kiện vào `ctx.model`. Ràng buộc mềm: thêm `(trọng số, biến)` vào
   `ctx.penalties`.
3. Thêm vào `default_hard_encoders()` (cứng) hoặc truyền vào `build_model(...)` (mềm).
4. Hàm mục tiêu (`ObjectiveBuilder`, P2) đọc `ctx.penalties` sau khi `build_model` chạy xong.

# Các encoder ràng buộc cứng

Mô hình được dựng bởi `build_model(problem, encoders=None)` trong
`infrastructure/solver/builder.py`: tạo biến `x[u,d,p,r]` rồi áp dụng lần lượt từng encoder.

| Encoder | Ý nghĩa |
|---|---|
| `each_unit_once` | Mỗi đơn vị học đúng một ô (ngày, tiết, phòng) |
| `room_no_overlap` | Một phòng, một ô: tối đa một đơn vị học |
| `teacher_no_overlap` | Một giáo viên, một ô: tối đa một đơn vị học |
| `class_no_overlap` | Một lớp, một ô: tối đa một đơn vị học |
| `max_consecutive_periods` | Một lớp không học liên tiếp quá `Problem.max_consecutive_periods` tiết (mặc định 2), tính theo số thứ tự tiết, chỉ áp dụng cho lớp |

Phòng cho phép theo loại (MBA vào G316, môn vẽ vào G313, hội trường không dùng) và tiết được phép
(1 đến 6) được áp dụng khi **tạo biến** (`variables.py` + `domain/services/room_policy.py`),
nên mô hình không có biến cho các ô bị cấm.

## Thêm một encoder mới
1. Viết lớp có `name: str` và `encode(self, ctx: ModelContext) -> None`.
2. Ràng buộc cứng: thêm điều kiện vào `ctx.model`. Ràng buộc mềm: thêm `(trọng số, biến)` vào
   `ctx.penalties`.
3. Thêm vào `default_hard_encoders()` (cứng) hoặc truyền vào `build_model(...)` (mềm).
4. Hàm mục tiêu (`ObjectiveBuilder`, P2) đọc `ctx.penalties` sau khi `build_model` chạy xong.

## Điểm cắm cho ràng buộc mềm và hàm mục tiêu (P2)
`build_model(problem, encoders=None, *, soft_encoders=(), objective=None)` chạy theo thứ tự:
1. Tạo biến `x[u,d,p,r]`.
2. Ràng buộc cứng (`encoders`, mặc định `default_hard_encoders()`).
3. Ràng buộc mềm (`soft_encoders`): mỗi encoder thêm `(trọng số, biến)` vào `ctx.penalties`.
4. Hàm mục tiêu (`objective`): đối tượng có `apply(ctx) -> None`, ví dụ gọi
   `ctx.model.minimize(sum(w * v for w, v in ctx.penalties))`.

`CpSatSolver(soft_encoders=[...], objective=...)` truyền các đối tượng này vào `build_model`, và
`SolveResult.objective` có giá trị khi mô hình có hàm mục tiêu. Xem ví dụ trong
`tests/unit/test_max_consecutive.py` (`SaturdayPenalty`, `MinimizePenalties`).

## Quy tắc tối đa 2 tiết liên tiếp
- Chỉ áp dụng cho lớp, giáo viên không bị giới hạn.
- Đếm theo chỉ số tiết: 3,4 hợp lệ; 2,3,4 bị cấm (nghỉ trưa không làm đứt chuỗi).
- Tiết bị cấm (7, 8) làm đứt chuỗi.
- Dùng `busy[c,d,p]` (bằng OR của các biến `x` của lớp `c` ở ngày `d`, tiết `p`); mỗi cửa sổ
  `max + 1` tiết liền nhau đều được phép xếp có tổng `busy <= max`.

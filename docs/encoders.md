# Các encoder ràng buộc cứng

Mô hình được dựng bởi `build_model(problem, encoders=None)` trong
`infrastructure/solver/builder.py`: tạo biến bắt đầu `s[u,d,p,r]` rồi áp dụng lần lượt từng
encoder. Các encoder đếm theo **các tiết bị chiếm**: đơn vị dài `duration` tiết bắt đầu ở tiết `p`
chiếm các tiết `p`, `p+1`, ... (hàm `occupancy_groups` trong `hard_encoders.py`).

| Encoder | Ý nghĩa |
|---|---|
| `each_unit_once` | Mỗi đơn vị học có đúng một ô bắt đầu (ngày, tiết, phòng) |
| `room_no_overlap` | Một phòng, một tiết: tối đa một đơn vị học |
| `teacher_no_overlap` | Một giáo viên, một tiết: tối đa một đơn vị học |
| `class_no_overlap` | Một lớp, một tiết: tối đa một đơn vị học |
| `max_consecutive_periods` | Một lớp không học liên tiếp quá `Problem.max_consecutive_periods` tiết (mặc định 2) |

Phòng cho phép theo loại (MBA vào G316, môn vẽ vào G313, hội trường không dùng), sức chứa, tiết
được phép (1 đến 6) và ô bắt đầu của block được áp dụng khi **tạo biến** (`variables.py`,
`room_policy.py`, `slot_policy.py`), nên mô hình không có biến cho các ô bị cấm.

## Thêm một encoder mới
1. Viết lớp có `name: str` và `encode(self, ctx: ModelContext) -> None`.
2. Ràng buộc cứng: thêm điều kiện vào `ctx.model`. Ràng buộc mềm: thêm `(trọng số, biến)` vào
   `ctx.penalties`.
3. Thêm vào `default_hard_encoders()` (cứng) hoặc truyền vào `build_model(...)` (mềm).
4. Thêm test kiểm tra cả trường hợp hợp lệ và vi phạm; kiểm tra chéo bằng `check_timetable`
   (`tests/solver_helpers.check_valid`).

## Điểm cắm cho ràng buộc mềm và hàm mục tiêu (P2)
`build_model(problem, encoders=None, *, soft_encoders=(), objective=None)` chạy theo thứ tự:
1. Tạo biến `s[u,d,p,r]`.
2. Ràng buộc cứng (`encoders`, mặc định `default_hard_encoders()`).
3. Ràng buộc mềm (`soft_encoders`): mỗi encoder thêm `(trọng số, biến)` vào `ctx.penalties`.
4. Hàm mục tiêu (`objective`): đối tượng có `apply(ctx) -> None`. Hàm mục tiêu của P2 được nối
   bằng `SoftObjectiveApplier` (hàm của P2 tự gọi `model.minimize`, nên đây phải là bước cuối).

`CpSatSolver(soft_encoders=[...], objective=...)` truyền các đối tượng này vào `build_model`.
`SolveResult.objective` có giá trị khi mô hình có hàm mục tiêu, và `SolveResult.cost_terms` trả
từng số hạng.

## Quy tắc tối đa 2 tiết liên tiếp
- Chỉ áp dụng cho lớp, giáo viên không bị giới hạn.
- Đếm theo chỉ số tiết, tính cả các tiết bị chiếm: block 2 tiết tính là 2 tiết. Ví dụ tiết 3,4
  hợp lệ; 2,3,4 bị cấm (nghỉ trưa không làm đứt chuỗi).
- Hệ quả với block: (1,2) rồi (5,6) trong cùng ngày hợp lệ; (1,2) rồi (3,4) là 4 tiết liền nên
  bị cấm.
- Tiết bị cấm (7, 8) làm đứt chuỗi.
- Dùng `busy[c,d,p]` (bằng OR của các biến bắt đầu làm lớp `c` bận ở ngày `d`, tiết `p`); mỗi
  cửa sổ `max + 1` tiết liền nhau đều được phép xếp có tổng `busy <= max`.

## Kiểm tra độc lập
`domain/services/timetable_checker.py::check_timetable(problem, timetable)` kiểm tra lại các ràng
buộc cứng mà không dùng CP-SAT, trả về danh sách `Violation`. `Validator` (`domain/validator.py`)
gọi hàm này khi được truyền `problem`. `SolveTimetable` chạy nó sau mỗi lần giải để phát hiện lịch
sai do lỗi mô hình.

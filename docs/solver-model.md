# Quy ước mô hình CP-SAT (P1 và P2 thống nhất)

Dữ liệu và luật thực tế xem `docs/requirements.md`. Các lớp và luồng xử lý xem
`docs/architecture.md`.

## Đơn vị học (LessonUnit) và block
Mỗi môn (`Course`) có `periods_per_week` tiết mỗi tuần. `domain/services/unit_splitter.py` tách số
tiết đó thành các **block** liên tiếp, ưu tiên block 2 tiết, phần lẻ là block 1 tiết:

| Số tiết/tuần | Các block |
|---|---|
| 1 | 1 |
| 2 | 2 |
| 3 | 2 + 1 |
| 4 | 2 + 2 |
| 5 | 2 + 2 + 1 |

Mỗi block là một `LessonUnit` với `duration` (1 hoặc 2). Nếu dữ liệu đầu vào đã có `lesson_units`
thì dùng nguyên danh sách đó; nếu không, `problem_loader` tự tách từ `courses`.

## Biến quyết định s[u, d, p, r]
- `u` = `LessonUnit.id`
- `d` = ngày, từ 0 (Thứ 2) đến 5 (Thứ 7)
- `p` = tiết **bắt đầu**, đánh số từ 0. Chỉ tạo biến khi mọi tiết bị chiếm
  (`p` đến `p + duration - 1`) đều là tiết được phép xếp (`TimeGrid.allowed_periods`, mặc định
  0 đến 5). Block 2 tiết không thể bắt đầu ở tiết cuối được phép.
- `r` = `Room.id`

`s[u, d, p, r]` là biến Boolean: bằng 1 nếu đơn vị `u` bắt đầu ở ngày `d`, tiết `p`, phòng `r` và
chiếm `duration` tiết liên tiếp từ đó. Khóa là tuple `(unit_id, day, period, room_id)` (kiểu
`VarKey` trong `infrastructure/solver/encoder.py`). `Assignment.period` trong kết quả cũng là tiết
bắt đầu.

Quan hệ với biến "đang học" của P2: `x[u, d, p, r] = s[u, d, p, r] + s[u, d, p-1, r]` (với block
2 tiết). Mô hình chỉ lưu `s`; các encoder đếm theo các tiết bị chiếm.

### Giới hạn ô bắt đầu của block
`Problem.block_starts` (JSON: `constraints.block_starts`) giới hạn tiết bắt đầu của block từ
2 tiết trở lên. Giá trị thực tế của trường là `[0, 2, 4]`: block chỉ căn theo cặp tiết 1-2, 3-4,
5-6. `None` nghĩa là bắt đầu ở tiết nào cũng được. Block 1 tiết luôn tự do.

### Chỉ tạo biến cho ô hợp lệ
Biến chỉ được tạo khi `room.can_host(unit.required_room_type)` và `room.capacity >= size` của
lớp (`domain/services/room_policy.py`), và ô bắt đầu hợp lệ (`domain/services/slot_policy.py`).
Mô hình không có biến cho các ô bị cấm.

## Giao diện encoder
Mỗi ràng buộc là một `ConstraintEncoder` có `name` và `encode(ctx: ModelContext)`.
- Ràng buộc cứng: thêm điều kiện vào `ctx.model`.
- Ràng buộc mềm: thêm `(trọng số, biến phạt)` vào `ctx.penalties`.
- Hàm mục tiêu: một `ObjectiveApplier` có `apply(ctx)`.
  `SoftObjectiveApplier` (`infrastructure/solver/soft_adapter.py`) nối hàm `add_soft_objective`
  của P2 vào mô hình thật, và lưu từng số hạng (`room`, `sat`, `g316`) vào `ctx.cost_terms`;
  `SolveResult.cost_terms` trả các giá trị đó.

## Ràng buộc mềm của P2 (xem `docs/soft-constraints.md`)
- `RoomStability`: offering = `Course.id`. Một môn tách thành nhiều ca vẫn là một offering; biến
  phiên học của offering là tổng các biến bắt đầu của các ca cùng môn.
- `AvoidSaturday`: phạt `W_SAT` cho mỗi **phiên** bắt đầu vào Thứ 7 (đếm `s`, không đếm từng tiết).
- `PreferMbaRoom`: phạt `W_G316` cho mỗi phiên của lớp không phải MBA ở G316.
- Quy tắc "tối đa 1 ca mỗi ngày cho một môn" **không phải** ràng buộc cứng: một môn được có ca
  thứ hai trong cùng ngày nếu còn thời gian và giáo viên rảnh.

## Quy ước chỉ số
- Mã nguồn đánh số tiết và ngày từ 0. Tài liệu của P2 đánh số tiết từ 1 (tiết 1 là chỉ số 0).
- `sat_days` truyền vào `SoftObjectiveApplier` tính từ 0 (Thứ Bảy là 5).

## Sức chứa theo block của một lớp
Quy tắc tối đa 2 tiết liên tiếp và `block_starts = [0, 2, 4]` khiến mỗi lớp chỉ học tối đa
**4 tiết mỗi ngày**, tức 24 tiết mỗi tuần khi học đủ 6 ngày. Các cách xếp một ngày (số block 2 tiết,
số block 1 tiết) của một lớp:

| Block 2 tiết | Block 1 tiết | Ví dụ (tiết 1 đến 6) |
|---|---|---|
| 2 | 0 | 1-2 và 5-6 |
| 1 | 2 | block 1-2, rồi tiết 4 và tiết 5 (mỗi tiết là một block 1 tiết) |
| 0 | 4 | tiết 1, 2, 4, 5 (mỗi tiết một block 1 tiết, không quá 2 tiết liền) |

Ví dụ (1,2) rồi (3,4) là 4 tiết liền, và thêm tiết 3 ngay sau block 1-2 là 3 tiết liền, đều bị cấm.

Hệ quả cho dữ liệu: một lớp có tối đa **8 môn 3 tiết** (8 block 2 tiết và 8 block 1 tiết đủ 24 tiết),
và tổng số tiết mỗi tuần của một lớp không được vượt 24. Khi gần mức này bài toán rất chặt và solver
giải chậm (xem benchmark trong PR ngày 8).

`domain/services/block_capacity.py` kiểm tra điều này không cần solver: `class_capacity_issues(problem)`
báo các lớp không thể xếp vừa. Đây là điều kiện **cần** (xét riêng từng lớp); với một lớp mà giáo viên
và phòng không tranh chấp, nó cũng là điều kiện **đủ** (đối chiếu với solver trong
`tests/unit/test_block_capacity.py`).

## Tách môn thành ca học và kiểm tra nhất quán
- `unit_splitter` tách `periods_per_week` thành block (xem bảng ở trên). Môn 3 tiết = block 2 + block 1;
  hai block có thể cùng một ngày nếu không tạo ra 3 tiết liền.
- `domain/services/unit_consistency.py::check_units_match_courses` kiểm tra mỗi môn: tổng `duration`
  của các ca bằng `periods_per_week`, lớp và giáo viên của ca trùng với môn, id ca không trùng,
  `duration` chỉ là 1 hoặc 2.
- `problem_from_dict` gọi kiểm tra này và ném `InvalidProblemError` khi dữ liệu không nhất quán.
- File mẫu cũ `docs/schema/input.sample.json` dùng các ca 1 tiết (vẫn hợp lệ). File
  `docs/schema/input.blocks.sample.json` để trống `lesson_units` nên loader tự tách thành block,
  kèm `constraints.block_starts = [0, 2, 4]`.

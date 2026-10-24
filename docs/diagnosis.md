# Chẩn đoán vô nghiệm

Khi không có lịch thỏa mọi ràng buộc cứng, hệ thống báo **vì sao** thay vì chỉ trả `INFEASIBLE`.

## Hai tầng
1. **Kiểm tra nhanh trước khi giải** (`domain/services/capacity_precheck.py`): sức chứa tuần của
   giáo viên, của tập phòng và của lớp (`teacher_capacity`, `room_capacity`, `class_capacity`).
   Vi phạm thì chắc chắn vô nghiệm, nên `SolveTimetable` trả ngay `INFEASIBLE` mà không gọi solver
   (`diagnosis.source = "precheck"`). Đây là cách duy nhất nhanh khi bài toán lớn (ví dụ 50 lớp với
   8 giáo viên: solver chạy hết thời gian mà không kết luận được).
2. **Lõi vô nghiệm của CP-SAT** (`unsat_core.py`): khi solver trả `INFEASIBLE`, `CpSatSolver`
   dựng lại mô hình ở chế độ chẩn đoán (`build_model(problem, diagnostic=True)`), gắn mỗi nhóm
   ràng buộc cứng vào một literal rồi hỏi CP-SAT tập literal gây vô nghiệm. Lõi được thu nhỏ bằng
   cách thử bỏ từng nhóm (tối đa 40 nhóm, 10 s). Kết quả nằm ở `SolveResult.conflict_groups`.
   (`diagnosis.source = "solver"`.) Mô hình chẩn đoán chỉ dùng khi đã vô nghiệm, không ảnh hưởng tốc độ
   giải thường.

## Tên nhóm
Dạng `loại:chủ thể`. Bảng loại và thông báo tiếng Việt nằm ở
`application/use_cases/describe_conflicts.py` (`KIND_MESSAGES`).

| Loại | Chủ thể | Nghĩa |
|---|---|---|
| `no_valid_room` (kiểm tra nhanh) | danh sách môn | Không có phòng nào hợp lệ cho các môn đó (thiếu phòng đúng loại hoặc sức chứa không đủ) |
| `each_unit_once` | id ca học | Ca học không còn ô hợp lệ (loại phòng, sức chứa, tiết cho phép). Chỉ báo riêng khi không có nhóm khác |
| `room_no_overlap` | id phòng | Phòng không đủ tiết cho các ca cần dùng |
| `teacher_no_overlap` | id giáo viên | Giáo viên được giao quá nhiều tiết |
| `class_no_overlap` | id lớp | Lớp có quá nhiều tiết so với số tiết xếp được |
| `max_consecutive_periods` | id lớp | Giới hạn tiết liên tiếp làm lớp không xếp vừa |

## Thêm ràng buộc cứng mới (quy ước cho P1/P2)
Trong `encode(ctx)`, khi `ctx.group_literals is not None`, gắn điều kiện vào literal của nhóm:

```python
cst = ctx.model.add(...)
if ctx.group_literals is not None:
    cst.only_enforce_if(ctx.group_literal(f"{self.name}:{owner}"))
```
Biến phụ định nghĩa (ví dụ `busy`) không gắn literal. Đặt thêm thông báo cho loại mới vào
`KIND_MESSAGES`, nếu không sẽ rơi vào câu chung "nhóm ... mâu thuẫn".

## Hiển thị
`GET /jobs/{id}/result` trả `diagnosis`. Giao diện Streamlit (`interfaces/ui/diagnosis_view.py`) gọi endpoint này khi job `DONE` và hiện lý do kèm gợi ý sửa khi `INFEASIBLE`. Các file mẫu lỗi để thử nằm ở `docs/samples/`.

## Định dạng JSON kết quả
Trường mới `diagnosis` (thêm vào, không đổi trường cũ), `null` khi có lịch hoặc không có lý do:
```json
{"status": "INFEASIBLE", "assignments": [],
 "diagnosis": {"source": "precheck",
   "issues": [{"code": "teacher_capacity", "message": "...", "suggestion": "..."}]}}
```
`source` là `precheck` hoặc `solver`.

## Giới hạn
- Lõi có thể chưa tối thiểu khi quá 40 nhóm hoặc hết 10 s.
- Chỉ ràng buộc cứng có literal. Ràng buộc nằm sẵn trong việc tạo biến (loại phòng, sức chứa,
  tiết cho phép) xuất hiện qua nhóm `each_unit_once`.
- Chưa chẩn đoán trạng thái `UNKNOWN` (hết thời gian), chỉ `INFEASIBLE`.

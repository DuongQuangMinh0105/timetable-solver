# Báo cáo lần giải đầu tiên (dữ liệu khó)

## 1. Kết quả chạy (seed 1)

- Seed: 1
- Tham số generator: `{'num_classes': 20, 'num_teachers': 8, 'num_mba_classes': 6, 'num_art_classes': 6}`
- Số ca học: 118
- Trạng thái solver: OPTIMAL
- Thời gian giải: 10.5s (giới hạn 30s, 2 workers)
- Lệnh chạy lại: `python scripts/run_first_solve.py --seed 1 --time-limit 30 --workers 2`
- Validator: 13 vi phạm, timetable_checker: 0 vi phạm

| Rule | Số vi phạm (Validator) |
|---|---|
| MAX_CONSECUTIVE | 13 |

Ví dụ:
- [HARD] MAX_CONSECUTIVE: Giáo viên T04 có quá 2 tiết liên tiếp vào ngày 1.
- [HARD] MAX_CONSECUTIVE: Giáo viên T02 có quá 2 tiết liên tiếp vào ngày 2.
- [HARD] MAX_CONSECUTIVE: Giáo viên T07 có quá 2 tiết liên tiếp vào ngày 0.

## 2. Phát hiện (cần P1 xác nhận)

### 2.1. Validator và timetable_checker mâu thuẫn
- Validator báo 13 vi phạm MAX_CONSECUTIVE, **cả 13 đều của giáo viên**. `check_timetable` báo 0.
- Nguyên nhân: rule "tối đa 2 tiết liên tiếp" chỉ áp cho **lớp** ở `hard_encoders.py`,
  `timetable_checker.py`, `block_capacity.py`; riêng `validator.py` (dòng 214) áp thêm cho **giáo viên**.
- **Câu hỏi cho P1: rule này áp cho lớp hay cả giáo viên?**
  - Chỉ lớp: sửa validator, bỏ vòng lặp giáo viên.
  - Cả giáo viên: solver và checker thiếu encoder cho giáo viên (việc của người làm solver).

### 2.2. Rule phòng theo loại lớp: MBA chạy, Vẽ không chạy
- Validator dò chuỗi trong `subject + class_group`: "MBA" cho G316, "VẼ"/"DRAWING" cho G313.
- Rule vẽ (sai): tiết `M-DES1-DRAW-0` (lớp `C-DES1`) xếp vào G314, Validator trả `[]`.
  Lệnh: `python -c "from timetable.infrastructure.generator import generate_v1; from timetable.infrastructure.problem_loader import problem_from_dict; from timetable.domain.validator import Validator; p=problem_from_dict(generate_v1(4,6,0)); u=next(x for x in p.lesson_units if 'DRAW' in x.id); print(Validator().validate([{'unit_id':u.id,'day':0,'period':0,'room_id':'G314'}], p))"`
- Rule MBA (đúng): tiết `M-MBA1-MGT-0` xếp vào G314, Validator trả `MBA_ROOM_VIOLATION`.
  Rule này đúng chỉ nhờ mã lớp `C-MBA1` tình cờ chứa chữ "MBA".
- Đề xuất: dùng `required_room_type` của lesson unit ("mba" / "art") thay vì dò chuỗi.

### 2.3. Thông báo lỗi sai
- `TEACHER_CONFLICT` và `CLASS_CONFLICT` đều ghi "Phòng {room} bị trùng lịch" (copy từ ROOM_CONFLICT).

### 2.4. Trùng lặp và lệch spec
- Hai bộ kiểm tra song song (`domain/validator.py`, `services/timetable_checker.py`) và hai lớp `Violation`.
- `docs/test-data-spec.md` ghi sĩ số trung bình 35, generator sinh 20-28 (sức chứa phòng 30).

### 2.5. Dữ liệu "khó" chưa đủ khó
- 20 lớp (6 MBA, 6 vẽ), 8 giáo viên, 118 ca học: OPTIMAL trong 10.5s với 2 workers.
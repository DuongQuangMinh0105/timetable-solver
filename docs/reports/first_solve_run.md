# Báo cáo lần giải đầu tiên (dữ liệu khó)

- Seed: 1
- Tham số generator: {'num_classes': 20, 'num_teachers': 8, 'num_mba_classes': 6, 'num_art_classes': 6}
- Số ca học: 118
- Trạng thái solver: OPTIMAL
- Thời gian giải: 9.6s (giới hạn 30.0s, 2 workers)
- Lệnh chạy lại: `python scripts/run_first_solve.py --seed 1 --time-limit 30.0 --workers 2`

- Validator: 5 vi phạm
- timetable_checker: 0 vi phạm

| Rule | Số vi phạm |
|---|---|
| MAX_CONSECUTIVE | 5 |

## Ví dụ
- [HARD] MAX_CONSECUTIVE: Giáo viên T04 có quá 2 tiết liên tiếp vào ngày 0.
- [HARD] MAX_CONSECUTIVE: Giáo viên T02 có quá 2 tiết liên tiếp vào ngày 3.
- [HARD] MAX_CONSECUTIVE: Giáo viên T07 có quá 2 tiết liên tiếp vào ngày 1.
- [HARD] MAX_CONSECUTIVE: Giáo viên T01 có quá 2 tiết liên tiếp vào ngày 0.
- [HARD] MAX_CONSECUTIVE: Giáo viên T05 có quá 2 tiết liên tiếp vào ngày 1.

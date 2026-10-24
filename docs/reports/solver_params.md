# Chốt tham số solver và trọng số (việc 14, 15, 17 của P2)

Số đo ngày 24/10/2026, bộ sinh `generate_hard` (giáo viên tăng theo số lớp), mục tiêu 5-10-2.
CP-SAT nhiều luồng không lặp lại chính xác giữa các lần chạy; "1 luồng" đo bằng `taskset -c 0`
(1 nhân thật, gần nhất với điều kiện Render).

## Kết quả cuối

| Số lớp | Luồng | Giới hạn (s) | Seed | Trạng thái | Mục tiêu | Thời gian (s) |
|---|---|---|---|---|---|---|
| 30 | 1 | 60 | 1 | FEASIBLE | 56 | 60,0 |
| 30 | 2 | 60 | 1 | OPTIMAL | 0 | 13,9 |
| 30 | 1 | 60 | 2 | OPTIMAL | 0 | 17,5 |
| 30 | 2 | 60 | 2 | OPTIMAL | 0 | 13,1 |
| 50 | 1 | 60 | 1 | FEASIBLE | 530 | 60,1 |
| 50 | 2 | 60 | 1 | FEASIBLE | 162 | 60,1 |
| 50 | 1 | 120 | 1 | FEASIBLE | 851 | 120,1 |
| 50 | 2 | 120 | 1 | FEASIBLE | 162 | 120,1 |

Nhận xét:
- 30 lớp với 2 luồng: tối ưu trong khoảng 13 s, ổn định giữa các seed.
- 30 lớp với 1 luồng: dao động lớn (seed 1 chưa tối ưu sau 60 s, seed 2 tối ưu sau 17 s).
- 50 lớp với 1 luồng: kết quả xấu và không cải thiện khi tăng giờ (530 rồi 851, do tìm kiếm
  ngẫu nhiên). Với 2 luồng, mục tiêu ổn định quanh 162 và cũng không giảm thêm khi tăng giờ.
- Đa số điểm phạt ở 50 lớp là buổi thứ Bảy bắt buộc (xem `scale_benchmark.md`), nên khoảng cách
  tới tối ưu thật có thể nhỏ hơn con số này.

## Tham số chốt

| Tham số | Giá trị | Lý do |
|---|---|---|
| `num_workers` | **2** trở lên (tối đa 4); đặt `SOLVER_MAX_WORKERS` cho nơi có ít nhân | 1 luồng không ổn định; 2 luồng đủ cho 30 lớp |
| `time_limit_s` | **120** cho demo 30 lớp (đo thực tế cần khoảng 13 đến 60 s); trần `SOLVER_MAX_TIME_S=300` | Dư địa cho Render chậm hơn máy đo; tăng quá 120 s không giúp 50 lớp |
| `AddHint` | **Tắt** | Không cải thiện (`hint_benchmark.md`, `scale_benchmark.md`) |
| Giải hai pha | **Không dùng** | Không tốt hơn một pha (`scale_benchmark.md`) |
| Encoder tối ưu (`optimization_encoders`) | **Tắt** | Làm xấu kết quả ở 50 lớp (`docs/encoders.md`) |
| Trọng số mềm | **5-10-2** (phòng, thứ Bảy, G316) | Xem bảng dưới |

Quy mô hỗ trợ cho demo: **30 lớp**. 50 lớp chạy được nhưng chỉ FEASIBLE, hiển thị đúng trạng thái
đó. 100 lớp cần nhiều phòng hơn dữ liệu sinh hiện có (12 phòng) và nhiều CPU, chưa hỗ trợ.

## Trọng số mềm: bộ trọng số, trước và sau
Trung bình 5 seed, 30 s, 2 luồng (`multi_seed_baseline.md`, P2). "Trước" là mặc định 5-10-2.

| Profile | Bộ trọng số | Mục tiêu TB | Phạt phòng | Phạt T7 | Phạt G316 |
|---|---|---|---|---|---|
| small, spec, tight_teachers | mọi bộ | 0 | 0 | 0 | 0 |
| many_mba | **5-10-2 (trước, mặc định)** | 20 | 0 | 20 | 0 |
| many_mba | 5-20-2 (ưu tiên tránh T7) | 40 | 0 | 40 | 0 |
| many_mba | 10-10-2 (ưu tiên ổn định phòng) | 20 | 0 | 20 | 0 |
| many_mba | 5-10-10 (ưu tiên G316) | 20 | 0 | 20 | 0 |

Kết luận: ba profile đầu không phân biệt được các bộ trọng số. Ở `many_mba` thứ Bảy là bắt buộc
(phòng G316 quá tải), nên tăng trọng số thứ Bảy chỉ nhân đôi điểm phạt chứ không tránh được thứ
Bảy. Các bộ còn lại bằng nhau. **Giữ 5-10-2.** Trọng số có thể đặt riêng từng bài toán qua khóa
`soft_weights` trong JSON (`room_stability`, `avoid_saturday`, `reserve_mba_room`). Chưa tinh chỉnh
được trên dữ liệu thật của trường vì chưa có; làm lại phép đo này khi có.

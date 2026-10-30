# Cấu hình ràng buộc (phiên bản 1.0)

Phiên bản hiện tại: `constraint_config_version = "1.0"` (hằng số `CONSTRAINT_CONFIG_VERSION` trong
`src/timetable/domain/constraint_config.py`).

- Đầu vào có thể khai `constraint_config_version`. Thiếu thì coi là phiên bản hiện tại.
  Phiên bản không được hỗ trợ bị từ chối: API trả 422, loader ném `InvalidProblemError`.
- Kết quả giải luôn có `constraint_config_version` để biết lịch được tạo theo bộ quy tắc nào.
- **Khi nào tăng phiên bản:** thêm, bỏ hoặc đổi ý nghĩa một ràng buộc cứng, đổi ràng buộc mềm hoặc
  ý nghĩa trọng số. Đổi giá trị mặc định của trọng số cũng tính. Cập nhật tài liệu này cùng lúc.

## Ràng buộc cứng (không bao giờ vi phạm)

| Mã | Nội dung | Nơi cài đặt |
|---|---|---|
| H1 | Mỗi ca học xếp đúng một lần | `EachUnitOnceEncoder` |
| H2 | Một phòng không có hai ca trùng thời điểm | `RoomNoOverlapEncoder` |
| H3 | Một giáo viên không dạy hai ca trùng thời điểm | `TeacherNoOverlapEncoder` |
| H4 | Một lớp không học hai ca trùng thời điểm | `ClassNoOverlapEncoder` |
| H5 | Tối đa `max_consecutive_periods` (mặc định 2) tiết liên tiếp mỗi lớp | `MaxConsecutiveEncoder` |
| H6 | Phòng phải đúng loại (MBA: G316, lớp vẽ: G313, còn lại phòng thường) | `room_policy.py`, `variables.py` |
| H7 | Chỉ xếp vào các tiết trong `allowed_periods`; block 2 tiết chỉ bắt đầu ở `block_starts` | `slot_policy.py` |

Chưa có ràng buộc sĩ số lớp so với sức chứa phòng: bộ sinh dữ liệu luôn đảm bảo sĩ số <= sức chứa.

Môn từ 3 tiết trở lên tách thành block 2+1 (xem `docs/solver-model.md`).

## Giới hạn dữ liệu (điều kiện cần, kiểm tra trước khi giải)

- Mỗi lớp tối đa **24 tiết/tuần** (mỗi ngày tối đa 4 tiết, 6 ngày); tối đa 8 môn 3 tiết mỗi lớp.
  Đã thử 30 tiết/lớp và không xếp được.
- Tổng số tiết của một giáo viên và của một nhóm phòng không được vượt sức chứa theo tuần.

## Ràng buộc mềm (trọng số mặc định, có thể ghi đè bằng `soft_weights`)

| Khóa `soft_weights` | Mặc định | Ý nghĩa |
|---|---|---|
| `room_stability` | 5 | Mỗi phòng khác nhau thêm vào của một môn (ngoài phòng đầu) |
| `avoid_saturday` | 10 | Mỗi buổi học xếp vào thứ Bảy |
| `reserve_mba_room` | 2 | Mỗi buổi của môn không phải MBA xếp vào G316 |

Chi tiết: `docs/soft-constraints.md`.

## Nhóm chuyên môn của giáo viên (kiểm tra dữ liệu)

Giáo viên và môn có thể khai cột tùy chọn `department` (ví dụ `IT`, `Business`, `Design`, `English`).
Nếu **cả hai** đều khai thì giáo viên phải cùng nhóm với môn mình dạy, nếu không dữ liệu bị từ chối
(API trả 422, giao diện báo lỗi) với thông báo tiếng Việt và gợi ý giáo viên cùng nhóm. Thiếu một
trong hai thì không giới hạn; so sánh không phân biệt hoa thường.

Đây là kiểm tra dữ liệu đầu vào (mỗi môn đã có sẵn một giáo viên), không phải ràng buộc của mô hình
CP-SAT, nên không đổi `constraint_config_version`. Mã: `domain/services/teacher_department.py`.
Số giáo viên mỗi nhóm không cố định: thêm hoặc bớt giáo viên chỉ cần sửa bảng Giáo viên.

## Lịch sử phiên bản

| Phiên bản | Nội dung |
|---|---|
| 1.0 | Bộ ràng buộc hiện tại: H1–H7 và ba ràng buộc mềm ở trên. |

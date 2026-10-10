# Dữ liệu và ràng buộc thực tế

Nguồn: thông tin nhà trường cung cấp. File này là chuẩn chung để P1, P2, P3, P5 đối chiếu.

## Thời gian
- Học từ Thứ 2 đến Thứ 7 (`day` 0 đến 5).
- Mỗi ngày có 8 tiết, nhưng **tiết 7 và 8 không được xếp lịch**. Tiết 1 đến 6 là `period` 0 đến 5.

| Tiết | Chỉ số | Giờ |
|---|---|---|
| 1 | 0 | 07:30 - 09:00 |
| 2 | 1 | 09:10 - 10:40 |
| 3 | 2 | 10:50 - 12:20 |
| 4 | 3 | 12:50 - 14:20 |
| 5 | 4 | 14:30 - 16:00 |
| 6 | 5 | 16:10 - 17:40 |
| 7 | 6 | 17:50 - 19:20 (không xếp) |
| 8 | 7 | 19:30 - 21:00 (không xếp) |

## Phòng
Sức chứa mỗi phòng khoảng 20 đến 30 chỗ. Giá trị trong dữ liệu mẫu là 30 (tạm thời, chờ số chính xác).

| Phòng | Vai trò | Loại trong mô hình |
|---|---|---|
| G314, G317, G318, G319 | Phòng học thường | `standard` |
| G502, G503, G504, G508, G509, G510 | Phòng học thường | `standard` |
| G316 | Phòng học, **bắt buộc cho lớp MBA**, lớp thường vẫn dùng được | `mba`, hỗ trợ thêm `standard` |
| G313 | Phòng hội họa, **chỉ lớp Design và chỉ đúng tiết vẽ** | `art` |
| G311, G312 | Hội trường, chỉ tổ chức sự kiện | **Loại khỏi bài toán** |
| G315, G320, G501, G505, G506, G507 | Tư vấn, kho, Director, Academic Affairs, thư viện, Student service | **Loại khỏi bài toán** |

Các phòng thường (G314, G317 đến G319, G502 đến G504, G508 đến G510) được giả định là phòng học dù
chưa có ghi chú; cần xác nhận lại.

## Ràng buộc cứng
1. Mỗi đơn vị học đúng một ô (ngày, tiết, phòng).
2. Một phòng, một ô chỉ có tối đa một đơn vị học.
3. Một lớp, một ô chỉ học một đơn vị. Một giáo viên, một ô chỉ dạy một đơn vị.
4. **Không xếp tiết 7 và 8.**
5. **Một lớp học tối đa 2 tiết liên tiếp** (tính theo số thứ tự tiết).
   - Hợp lệ: tiết 1, 2 rồi nghỉ, sau đó tiết 5, 6; hoặc tiết 3, 4.
   - Không hợp lệ: tiết 2, 3, 4 (3 tiết liền nhau, dù có nghỉ trưa giữa tiết 3 và 4).
   - Chỉ áp dụng cho **lớp**. Giáo viên không bị giới hạn này, chỉ cần rảnh giờ đó.
6. Đơn vị học chỉ vào phòng có `can_host(required_room_type)` và đủ sức chứa.
   - Lớp MBA chỉ vào G316. Lớp Design chỉ vào G313 khi học môn vẽ. Hội trường không dùng.

## Ràng buộc mềm (P2 phụ trách, có trọng số)
1. **Hạn chế Thứ 7** (`AvoidSaturday`): phạt mỗi tiết xếp vào Thứ 7.
2. **Hạn chế đổi phòng** (`RoomStability`): **theo từng môn của lớp**, các tiết của cùng một môn nên
   ở cùng một phòng. Khóa `k` = `Course.id` (mỗi `Course` đã gắn một lớp).
3. **Ưu tiên lớp MBA ở G316** (`reserve_mba_room`): phạt nhẹ khi lớp thường dùng G316, để chừa chỗ cho MBA.

## Câu hỏi còn mở
- Sức chứa chính xác của từng phòng.
- Danh sách lớp, môn, giáo viên (khoảng 20 giáo viên) và số tiết mỗi tuần của từng môn.
- Giáo viên có ngày hoặc tiết bận cố định không.

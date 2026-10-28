# Giao diện: sửa dữ liệu đầu vào và sửa kết quả

Chạy giao diện: xem mục "Giao diện (Streamlit)" trong `README.md`.

## 1. Sửa dữ liệu đầu vào
1. Thanh bên: tải file Excel (mẫu tiếng Việt hoặc tiếng Anh, xem `docs/samples/`) rồi bấm **Đọc file**.
2. Tab **Dữ liệu đầu vào**: sửa trực tiếp 4 bảng (Phòng, Giáo viên, Lớp, Môn) và tab **Lưới giờ**
   (số ngày, số tiết mỗi ngày, các tiết được xếp, đánh số từ 1). Thêm dòng ở cuối bảng; chọn dòng rồi
   bấm Delete để xóa.
3. Bấm **Lưu và giải**. Dữ liệu được kiểm tra (thiếu ô, trùng id, lớp hay giáo viên không có, số
   không hợp lệ, lưới sai) và hiện lỗi tiếng Việt; hợp lệ thì gửi API để giải.
Mã nguồn: `interfaces/ui/tables.py` (không phụ thuộc streamlit, có test).

## 2. Sửa kết quả
Tab **Kết quả và chỉnh sửa**, mục **Sửa kết quả** (chỉ hiện khi có lịch):
- Sửa cột `day`, `start_period` (số từ 0) và `room_id` (chọn từ danh sách phòng). Các cột còn lại chỉ đọc.
- **Kiểm tra**: gọi `POST /jobs/{id}/validate`, hiện số vi phạm cứng, mềm và điểm phạt, không lưu gì.
- **Lưu bản sửa**: gọi `PUT /jobs/{id}/result/edited`; bản gốc của bộ giải được giữ nguyên.
  Vi phạm được báo nhưng không chặn việc lưu.
- **Giải lại, giữ ca đã sửa/khóa**: gửi lại bài toán kèm `fixed_assignments` gồm các ca đã sửa và các
  ca đánh dấu `locked`; bộ giải xếp phần còn lại quanh chúng. Nếu các ca khóa mâu thuẫn nhau thì
  nhận chẩn đoán vô nghiệm (xem `docs/diagnosis.md`).
- **Tải lịch đã sửa**: xuất Excel từ bảng đang sửa.
Mã nguồn: `interfaces/ui/result_edit.py` (có test) và hàm `render_editor` trong `app.py`.

## Giới hạn
- Chưa kéo thả trên lưới lịch: sửa theo từng dòng.
- Bản sửa gắn với job: giải lại tạo job mới nên bản sửa cũ không tự chuyển sang.
- `unavailable_slots` và `fixed_day`/`fixed_period` trong file Excel mẫu tiếng Anh vẫn bị bỏ qua
  (xem `docs/known-issues.md`).

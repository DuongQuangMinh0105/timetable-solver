# Triển khai lên Render (miễn phí) với Neon

## Kiến trúc

- **Neon**: PostgreSQL quản lý (bảng `jobs` và `blobs`).
- **Render** (web service Docker, gói free): chạy API. Worker chạy như tiến trình con của API
  (`LocalJobDispatcher`). File input và kết quả nằm trong bảng `blobs` (`STORAGE_BACKEND=postgres`)
  vì Render miễn phí không có ổ đĩa bền.
- Cấu hình nằm trong `render.yaml` ở thư mục gốc repo.

## Biến môi trường

| Biến | Giá trị | Ghi chú |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://<user>:<password>@<host>/<db>?sslmode=require` | Chuỗi kết nối Neon. Nhập trong Render Dashboard, **không commit** |
| `STORAGE_BACKEND` | `postgres` | `local` (mặc định) dùng thư mục `STORAGE_DIR` |
| `SOLVER_MAX_WORKERS` | `1` | Giới hạn số luồng của bộ giải, vì Render miễn phí chỉ có 0,1 CPU |
| `SOLVER_MAX_TIME_S` | tùy chọn, ví dụ `300` | Trần thời gian giải (giây); nhỏ hơn yêu cầu trong input thì lấy giá trị nhỏ hơn. Xem lưu ý CPU bên dưới |
| `PORT` | do Render đặt | Không cần tự đặt |

## Triển khai lần đầu

1. **Neon**: tạo project, copy chuỗi kết nối, đổi `postgresql://` thành `postgresql+psycopg://`
   (giữ `?sslmode=require`).
2. **Render**: New, chọn **Blueprint**, chọn repo, chọn nhánh `main`. Render đọc `render.yaml` và hỏi
   giá trị `DATABASE_URL`.
3. Render build image rồi chạy `alembic upgrade head` trước khi bật API.
4. Kiểm tra: `curl.exe https://<tên-dịch-vụ>.onrender.com/health` trả về `{"status":"healthy"}`.

## Chạy thử

```powershell
curl.exe -X POST https://<tên-dịch-vụ>.onrender.com/solve -H "Content-Type: application/json" --data-binary "@docs/schema/input.sample.json"
```

Trả về mã 202 kèm `job_id`. Xem trạng thái và kết quả trong Neon, mục **SQL Editor**:

```sql
select id, status, result_ref from jobs order by id desc limit 5;
select convert_from(data, 'UTF8') from blobs where key = 'jobs/<job_id>/result.json';
```

## Giới hạn của gói miễn phí

- Dịch vụ tự ngủ sau 15 phút không có truy cập và mất khoảng một phút để chạy lại, nên request đầu
  tiên sau khi ngủ rất chậm. Trước buổi demo hãy gọi `/health` để đánh thức.
- Chỉ 0,1 CPU và 512 MB RAM: bài toán lớn có thể hết thời gian giải (`time_limit_s`) và trả về
  `FEASIBLE` hoặc `UNKNOWN`.
- Dịch vụ có thể bị khởi động lại bất cứ lúc nào. Job đang chạy lúc đó sẽ kẹt ở trạng thái `running`.
- File lưu trong Postgres nên bị giới hạn bởi dung lượng gói Neon (chỉ hợp với file JSON nhỏ).
- Chưa có endpoint xem trạng thái hay kết quả job.

## Lưu ý tài nguyên của bộ giải

- Worker log dòng `Giải với num_workers=..., time_limit_s=...` kèm giá trị người dùng yêu cầu, để biết
  số luồng và thời gian thực dùng sau khi bị giới hạn bởi `SOLVER_MAX_WORKERS` và `SOLVER_MAX_TIME_S`.
- Đo cục bộ (bộ "khó": 20 lớp, 8 giáo viên, 118 ca học, seed 1): giải xong trạng thái `OPTIMAL` trong
  khoảng 10 giây với 1 CPU đầy đủ (cả 1 và 2 luồng). Đây là thời gian **CPU**: Render miễn phí chỉ có
  0,1 CPU nên thời gian thực (wall time) có thể dài hơn khoảng 10 lần (ước tính, chưa đo trên Render).
  `time_limit_s` của solver là thời gian thực, nên nếu CPU quá ít, nghiệm có thể chỉ là `FEASIBLE`
  hoặc `UNKNOWN`. Nâng `time_limit_s` trong input (ví dụ 180 giây) nếu gặp trường hợp này.
- Không build được Docker trong môi trường kiểm tra nên chưa đo trực tiếp trong container.

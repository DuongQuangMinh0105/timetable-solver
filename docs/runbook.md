# Runbook staging (Render + Neon)

Địa chỉ dịch vụ: xem ở đầu trang dịch vụ `timetable-solver` trong Render Dashboard
(dạng `https://timetable-solver-xxxx.onrender.com`). Cơ sở dữ liệu: Neon, project `timetable-solver`.
Biến môi trường và giới hạn của gói miễn phí: xem `docs/deploy-render.md`.

## Kiểm tra nhanh sau mỗi lần deploy

```powershell
$env:API_KEY = Read-Host "Dán API_KEY"
uv run python scripts/smoke_test.py https://<địa-chỉ>
```
Khóa `API_KEY` lấy từ nơi lưu bí mật của nhóm (trùng với giá trị trong Render, tab Environment).
Smoke test cũng kiểm tra job có lịch thật, nên job hết giờ giải (`UNKNOWN`) bị báo lỗi.

Kịch bản demo nhỏ và dữ liệu đầu vào dùng chung nằm trong [docs/demo-api.md](demo-api.md).

Kết quả đúng kết thúc bằng `SMOKE TEST OK`, kèm thời gian giải. Lần gọi đầu sau khi dịch vụ ngủ có
thể mất khoảng một phút, script tự chờ tối đa 120 giây. Script thoát mã 1 nếu `/health` không lên,
`POST /solve` lỗi hoặc job `FAILED`/quá hạn.

## Deploy

- Merge vào `main`: Render chỉ tự deploy sau khi CI trên GitHub xanh (`autoDeployTrigger: checksPass`).
  Theo dõi ở Render, dịch vụ `timetable-solver`, tab **Events**.
- Deploy tay: Render, dịch vụ, **Manual Deploy**, **Deploy latest commit**.
- Migration (`alembic upgrade head`) tự chạy mỗi lần dịch vụ khởi động.
- Deploy lỗi thì bản cũ vẫn chạy (Render chỉ chuyển lưu lượng khi bản mới qua `/health`).
- Sau mỗi lần merge vào main, workflow Smoke test sau deploy tự kiểm tra bản mới (xem tab Actions). Có thể mất 5 đến 15 phút vì phải chờ Render build.

## Xem log

Cảnh báo tự động và các truy vấn kiểm tra job lỗi: xem `docs/monitoring.md`.
Render, dịch vụ, tab **Logs**. Tìm `Job` (kết quả từng job), `Worker started`, `Traceback` (lỗi).
Các dòng `GET /health` mỗi 5 giây là Render tự kiểm tra, bình thường.

## Rollback

1. Nếu tab **Events** có nút Rollback ở một lần deploy cũ đã thành công, dùng nút đó.
2. Cách chắc chắn: `git revert <commit>` trên một nhánh mới, mở Pull Request, merge sau khi CI xanh.
   Render sẽ tự deploy lại.

Rollback code không hoàn tác migration của cơ sở dữ liệu.

## Sự cố thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| `POST /solve` trả `Internal Server Error` | Xem Logs, tìm `Traceback`. Nếu là `redis...ConnectionError` thì kiểm tra `JOB_DISPATCHER=local` còn trong `render.yaml` và Environment |
| Request đầu tiên rất chậm | Dịch vụ ngủ sau 15 phút không dùng; gọi `/health` đánh thức trước buổi demo |
| Job kẹt `RUNNING` quá vài phút | Dịch vụ có thể đã khởi động lại giữa chừng. Trong Neon SQL Editor, khi chắc không có job nào đang chạy: `update jobs set status = 'failed' where status = 'running';` |
| Merge xong mà Render không deploy | CI trên `main` đỏ hoặc chưa chạy xong (xem tab Actions trên GitHub) |
| Lỗi kết nối cơ sở dữ liệu | Kiểm tra `DATABASE_URL` trong Render, mục Environment: phải bắt đầu bằng `postgresql+psycopg://` và có `?sslmode=require` |

## Bí mật

`DATABASE_URL` chỉ nằm trong Render, mục Environment, không nằm trong repo. Đặt lại mật khẩu Neon:
vào project trong Neon, đặt lại mật khẩu của role, cập nhật `DATABASE_URL` trong Render rồi lưu
(Render sẽ deploy lại).
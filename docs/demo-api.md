# Demo API

Kịch bản này gửi một bài toán nhỏ qua API thật, theo dõi job bằng API và kiểm tra lịch kết quả.

## Dữ liệu demo

`docs/schema/api-demo.sample.json` có một lớp, hai môn, hai giáo viên và một phòng. Bài toán cần
xếp hai ca học một tiết trong bốn tiết khả dụng; kết quả hợp lệ có hai assignments và không có
violation. File này dùng được trực tiếp với `POST /solve`.

## Chạy local bằng Docker Compose

Yêu cầu Docker Desktop. Từ thư mục gốc repo, đặt khóa dùng riêng cho môi trường local và khởi chạy:

```powershell
$env:API_KEY = Read-Host "Nhập API_KEY local"
docker compose up -d --build
```

Compose khởi chạy PostgreSQL, migration, Redis, API và worker. Sau khi API sẵn sàng:

```powershell
uv run python scripts/smoke_test.py http://localhost:8000 `
  --input docs/schema/api-demo.sample.json --timeout 60 --poll 1
```

Thành công kết thúc bằng `SMOKE TEST OK`; script in job status và số assignments. Để xem tài liệu API,
mở `http://localhost:8000/docs`. Dừng các dịch vụ sau demo bằng `docker compose down`.

## Chạy với staging

Lấy `API_KEY` và URL từ nơi lưu bí mật/Dashboard của môi trường; không ghi khóa vào file hoặc commit:

```powershell
$env:API_KEY = Read-Host "Nhập API_KEY staging"
uv run python scripts/smoke_test.py https://<địa-chỉ-dịch-vụ> `
  --input docs/schema/api-demo.sample.json --timeout 300 --poll 5
```

Script thực hiện `GET /health`, `POST /solve`, poll `GET /jobs/{job_id}`, sau đó gọi
`GET /jobs/{job_id}/result`. Health check công khai; các endpoint còn lại cần header `X-API-Key`.
Nếu job bị `FAILED`, chưa có kết quả đúng hạn hoặc solver không tạo lịch, script trả mã thoát khác 0.

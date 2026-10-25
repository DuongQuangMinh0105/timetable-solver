# Bảo mật staging

## Đã làm
- Bí mật (`DATABASE_URL`, `API_KEY`) chỉ nằm trong Render, mục Environment, và trong kho mật khẩu
  của nhóm. Đã quét cây file và lịch sử Git: chưa từng có bí mật nào được commit.
- Mật khẩu Neon đã được đặt lại ngày `25/10`.
- `/solve` và `/jobs/...` đòi header `X-API-Key` (so sánh bằng `secrets.compare_digest`). Chỉ `/health`
  không cần khóa.
- Kết nối tới Neon dùng `sslmode=require`, Render cung cấp HTTPS.
- Workflow GitHub Actions chạy với quyền chỉ đọc (`permissions: contents: read`).

## Rà soát định kỳ
- Quét lịch sử tìm bí mật: `git log --all "-S<giá trị bí mật>" --oneline`. Không in gì là đạt.
- 2FA bật cho GitHub, Render, Neon. Render và Neon chỉ có đúng một dịch vụ/project của dự án.
- Đổi khóa: đặt giá trị mới trong Render (Environment), cập nhật kho mật khẩu, báo mọi người dùng khóa cũ.

## Giới hạn đã biết
- Ứng dụng dùng role `neondb_owner` (toàn quyền) vì dịch vụ chạy migration lúc khởi động và cả hai
  khóa nằm cùng container. Muốn tách role chỉ-đọc-ghi cho ứng dụng thì phải chạy migration ở bước riêng.
- Chỉ có một `API_KEY` chung, chưa có khóa theo từng người dùng và chưa giới hạn tần suất gọi.
- `/docs` và `/openapi.json` công khai trên staging. `/health` lộ mã commit đang chạy (trên Render).
- Dữ liệu job tích lũy trong bảng `jobs` và `blobs` của Neon, chưa có cơ chế tự xóa job cũ.
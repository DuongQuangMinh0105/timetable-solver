# Môi trường và cách dựng lại

## Tổng quan
| Môi trường | Chạy ở đâu | Cấu hình ở đâu |
|---|---|---|
| Local | docker compose | `compose.yaml`, `.env.example` |
| CI | GitHub Actions | `.github/workflows/ci.yml` |
| Staging | Render + Neon | `render.yaml`, Render Dashboard (bí mật) |

## Staging
- **Render**: dịch vụ `timetable-solver`, runtime Docker, gói free, region Oregon (US West),
  health check `/health`, tự deploy sau khi CI trên GitHub xanh.
- **Neon**: project `timetable-solver`, Postgres 18, region AWS Asia Pacific 1 (Singapore),
  database `neondb`, role `neondb_owner` (mật khẩu không ghi ở đây).
- **Biến môi trường** (chi tiết ở `docs/deploy-render.md`): `DATABASE_URL` (bí mật),
  `STORAGE_BACKEND=postgres`, `JOB_DISPATCHER=local`, `SOLVER_MAX_WORKERS=1`.
- **Lưu ý phiên bản**: staging dùng Postgres 18 còn local và CI dùng Postgres 17 (`compose.yaml`,
  `ci.yml`). Chưa thấy khác biệt nào ảnh hưởng, nếu cần đồng bộ thì đổi image sang 18.
- **Độ trễ**: Render ở Oregon còn Neon ở Singapore, nên mỗi truy vấn DB mất thêm khoảng vài trăm
  mili giây. Chấp nhận được cho staging; muốn nhanh hơn thì tạo lại dịch vụ Render ở region Singapore.

## Bí mật nằm ở đâu
- `DATABASE_URL`: trong Render, mục Environment. Bản dự phòng nằm trong trình quản lý mật khẩu
  (hoặc ghi chú mã hóa) do hai người giữ: Khoa (`nlakhoa123`) và Minh (`DuongQuangMinh0105`).
- Tuyệt đối không gửi bí mật qua chat và không commit vào repo.

## Dựng lại từ đầu (khoảng 30 phút)
1. Neon: tạo project, copy chuỗi kết nối, đổi `postgresql://` thành `postgresql+psycopg://` và giữ
   `?sslmode=require`.
2. Render: New, Blueprint, chọn repo và nhánh `main`, nhập `DATABASE_URL`.
3. Chờ dịch vụ **Live** (migration tự chạy khi khởi động).
4. Chạy `uv run python scripts/smoke_test.py https://<địa-chỉ>`, phải in `SMOKE TEST OK`.
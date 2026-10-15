# Hướng dẫn cài đặt môi trường phát triển

## Yêu cầu

- Python 3.11 và [uv](https://docs.astral.sh/uv/)
- Git
- Docker Desktop (chạy Postgres, API và worker bằng compose)
- `make` (không bắt buộc). Windows: `winget install ezwinports.make`, rồi đóng và mở lại PowerShell

## Cài đặt lần đầu

```powershell
git clone https://github.com/DuongQuangMinh0105/timetable-solver.git
cd timetable-solver
uv sync --locked
uv run pre-commit install
```

Windows PowerShell cũ không hiểu `&&`, nên chạy từng lệnh riêng.

## Kiểm tra code (giống CI)

Một số test cần Postgres và biến `DATABASE_URL`. Mở Docker Desktop rồi:

```powershell
docker compose up -d postgres
$env:DATABASE_URL = "postgresql+psycopg://timetable:timetable_dev@localhost:5432/timetable"
uv run alembic upgrade head
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Xong thì dọn: `Remove-Item Env:DATABASE_URL` và `docker compose down`.

Trước khi mở Pull Request, chạy `uv run pre-commit run --all-files` cho đến khi cả 3 dòng `Passed`.

## Chạy bằng Docker Compose

```powershell
make up
```

Nếu không có `make`, dùng `docker compose up --build`. Chạy nền: `docker compose up -d --build`.

| Dịch vụ | Mô tả | Địa chỉ |
|---|---|---|
| `postgres` | Cơ sở dữ liệu | `localhost:5432` |
| `migrate` | Chạy `alembic upgrade head` rồi thoát (trạng thái `Exited (0)` là bình thường) | không có cổng |
| `api` | FastAPI | `http://localhost:8000/health` |
| `worker` | Chờ job. Có biến `JOB_ID` thì chạy job đó rồi thoát | không có cổng |

`api` và `worker` dùng chung thư mục `data/storage` trên máy (mount vào `/app/data/storage` trong container). Thư mục `data/` không được commit.

Lần build đầu có thể mất 10-30 phút vì phải tải thư viện. Các lần sau nhanh nhờ cache, nên sửa code trong `src/` không phải tải lại thư viện.

Dừng bằng `make down` (hoặc `docker compose down`), xem log bằng `make logs`.

## Chạy thử một job (end-to-end)

Với compose đang chạy, có hai cách. Cả hai đều chạy bộ giải CP-SAT thật, có ràng buộc mềm (tránh thứ Bảy, một phòng cho mỗi môn, để dành G316 cho MBA).

**Cách 1: gửi bài toán qua API.** API lưu input, tạo job và tự chạy worker (tiến trình con trong container `api`):

```powershell
curl.exe -X POST http://localhost:8000/solve -H "Content-Type: application/json" --data-binary "@docs/schema/input.sample.json"
```

Kết quả trả về mã 202 kèm `job_id`. Chờ vài giây rồi xem trạng thái:

```powershell
docker compose exec postgres psql -U timetable -d timetable -c "select id, status, result_ref from jobs order by id desc limit 3;"
```

**Cách 2: tạo job mẫu rồi chạy worker bằng tay:**

```powershell
$env:DATABASE_URL = "postgresql+psycopg://timetable:timetable_dev@localhost:5432/timetable"
$id = (uv run python scripts/seed_job.py).Trim()
docker compose run --rm -e JOB_ID=$id worker
```

`seed_job.py` nhận thêm đường dẫn file input (mặc định `docs/schema/input.sample.json`).

Kiểm tra kết quả (thay `<id>` bằng `job_id` ở cách 1, hoặc dùng `$id` ở cách 2):

```powershell
$r = Get-Content data\storage\jobs\<id>\result.json -Raw -Encoding utf8 | ConvertFrom-Json; $r.status; $r.objective; $r.assignments.Count
```

Mong đợi: job `completed`, `status` là `OPTIMAL` hoặc `FEASIBLE`, `objective` là tổng điểm phạt mềm (0 là không bị phạt). Với dữ liệu mẫu `assignments.Count` là 25.

Cấu trúc `result.json`:

```json
{
  "status": "OPTIMAL",
  "objective": 15,
  "cost_terms": {"room": 5, "sat": 10, "g316": 0},
  "assignments": [
    {"unit_id": "M-A1-ENG-0", "course_id": "M-A1-ENG", "class_id": "C-A1",
     "teacher_id": "T01", "day": 0, "start_period": 0, "duration": 2, "room_id": "G314"}
  ],
  "violations": [{"rule_id": "...", "description": "...", "severity": "HARD"}]
}
```

- `start_period` là tiết bắt đầu (tính từ 0). Đơn vị học chiếm `duration` tiết liên tiếp từ đó.
- `status` nhận `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `UNKNOWN`, `MODEL_INVALID`. Vô nghiệm hoặc hết thời gian thì `assignments` rỗng.
- `objective` và `cost_terms` là điểm phạt mềm. Trọng số lấy từ `soft_weights` trong input (`room_stability`, `avoid_saturday`, `reserve_mba_room`).
- Không có lời giải (`INFEASIBLE`, `UNKNOWN`) vẫn là kết quả hợp lệ, job `completed`. Lịch vi phạm ràng buộc cứng thì job `failed` và không có `result.json`, xem lý do trong log: `docker compose logs api`.

Hiện chưa có endpoint xem trạng thái hay kết quả job.

## Chạy ở máy, không dùng Docker

- `LocalStorage` (`infrastructure/storage/local.py`): lưu file vào một thư mục. Key như `jobs/1/input.json` thành đường dẫn con. Key trỏ ra ngoài thư mục gốc (ví dụ `../x`) bị từ chối.
- `LocalJobDispatcher` (`infrastructure/dispatch/local.py`): chạy worker như một tiến trình riêng, truyền `job_id` qua biến môi trường `JOB_ID`.
- API và worker cùng đọc `DATABASE_URL` (Postgres) và `STORAGE_DIR` (mặc định `data/storage`). Hai tiến trình phải trỏ cùng một thư mục, nếu không worker không thấy file input.

## Quy trình làm việc

1. Tạo nhánh riêng từ `main`.
2. Commit, đẩy lên rồi mở Pull Request.
3. Chờ job `ci` xanh và có người duyệt, rồi merge.
4. Sau khi merge: `git checkout main`, `git pull`, `uv sync --locked`.

## Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `No module named 'ortools'` hoặc `import-not-found` | Chạy `uv sync --locked` (thiếu thư viện trong môi trường) |
| `DATABASE_URL is missing` | Đặt biến `DATABASE_URL` như phần "Kiểm tra code" ở trên |
| `ruff format --check` báo file cần sửa | Chạy `uv run ruff format .` |
| `make` không được nhận | Cài `make`, đóng và mở lại PowerShell, hoặc dùng `docker compose` |
| `docker daemon is not running` | Mở Docker Desktop và đợi biểu tượng báo "running" |
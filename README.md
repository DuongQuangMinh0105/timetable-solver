uv sync
uv run pytest
uv run ruff check .
uv run mypy

Yêu cầu: Python 3.11, uv.

## Công nghệ
- Solver: Python 3.11 + OR-Tools CP-SAT (num_workers = số vCPU)
- API: FastAPI + Pydantic + uvicorn, đóng gói Docker
- CSDL: PostgreSQL + SQLAlchemy + Alembic
- Kiểm thử/chất lượng: pytest, ruff, mypy, pre-commit
- Repo và CI/CD: GitHub + GitHub Actions; IaC: Terraform (thư mục `infra/`)

## Luồng hoạt động
1. Client gửi JSON đến `POST /solve`.
2. API lưu job và đưa vào hàng đợi; worker chạy CP-SAT.
3. Client gọi `GET /jobs/{job_id}` để theo dõi trạng thái.
4. Khi job hoàn tất, client gọi `GET /jobs/{job_id}/result` để lấy lịch và kết quả kiểm tra.

## API

API có tài liệu tương tác tại `/docs` (Swagger UI), `/redoc` (ReDoc) và OpenAPI JSON tại
`/openapi.json`. Ví dụ nếu chạy local ở cổng 8000: `http://localhost:8000/docs`.

| Endpoint | Xác thực | Mô tả |
|---|---|---|
| `GET /health` | Không | Health check, trả `{"status":"healthy"}` |
| `POST /solve` | `X-API-Key` | Nhận JSON theo [schema mẫu](docs/schema/input.sample.json), trả HTTP 202 với `job_id` và trạng thái `queued` |
| `GET /jobs/{job_id}` | `X-API-Key` | Trả `job_id`, trạng thái (`QUEUED`, `RUNNING`, `DONE`, `FAILED`) và `result_ref` |
| `GET /jobs/{job_id}/result` | `X-API-Key` | Trả trạng thái solver, objective, assignments và violations khi kết quả đã sẵn sàng |

Đặt biến môi trường `API_KEY` cho API và gửi cùng giá trị trong header `X-API-Key` ở cả ba endpoint
bảo vệ. Thiếu hoặc sai khóa trả HTTP 401. `GET /jobs/{job_id}` và endpoint result trả HTTP 404 nếu
không tìm thấy job; endpoint result trả HTTP 409 khi kết quả chưa sẵn sàng. Request không hợp lệ
trả HTTP 422. Chi tiết request/response được mô tả trong OpenAPI.

Ví dụ vòng đời job (PowerShell):

```powershell
$env:API_KEY = Read-Host "Nhập API_KEY"
$headers = @{ "X-API-Key" = $env:API_KEY }
$payload = Get-Content -Raw docs/schema/input.sample.json
$accepted = Invoke-RestMethod -Method Post -Uri http://localhost:8000/solve `
  -Headers $headers -ContentType "application/json" -Body $payload
$jobId = $accepted.job_id
$deadline = (Get-Date).AddMinutes(2)
do {
  $job = Invoke-RestMethod -Uri "http://localhost:8000/jobs/$jobId" -Headers $headers
  if ($job.status -in @("DONE", "FAILED")) { break }
  Start-Sleep -Seconds 1
} while ((Get-Date) -lt $deadline)
if ($job.status -ne "DONE") { throw "Job ended with status $($job.status)" }
Invoke-RestMethod -Uri "http://localhost:8000/jobs/$jobId/result" -Headers $headers
```

Nếu cần chờ worker hoàn tất và kiểm tra lịch mẫu tự động, xem [kịch bản demo API](docs/demo-api.md).

## Giao diện (Streamlit)

Chạy API trước (xem trên), rồi chạy giao diện với cùng `API_KEY`:

```powershell
$env:API_URL = "http://localhost:8000"
$env:API_KEY = "<cùng khóa với API>"
uv run streamlit run src/timetable/interfaces/ui/app.py
```

Mở `http://localhost:8501`, tải một file Excel (ví dụ `docs/samples/ok_basic.xlsx`), bấm **Đọc file**, sửa dữ liệu nếu cần rồi bấm **Lưu và giải**; sau khi có lịch có thể sửa kết quả ([hướng dẫn](docs/ui-editing.md)). Các file
`docs/samples/fail_*.xlsx` cố tình sai dữ liệu để xem chẩn đoán vô nghiệm bằng tiếng Việt. Giải thích
mô hình: [docs/model-explained.md](docs/model-explained.md).

## Kiến trúc (Clean Architecture)

src/timetable/
domain/ # entity, rules, services (không import tầng nào khác)
application/ # use_cases, ports, dto (chỉ import domain)
infrastructure/ # solver, persistence, storage, dispatch (hiện thực port)
interfaces/ # api, worker, ui

**Quy tắc phụ thuộc:** tầng trong không bao giờ import tầng ngoài.
domain <- application <- infrastructure, interfaces.

## Quy ước làm việc
- Nhánh: `feature/<tên>-<việc>`; không push thẳng vào `main`, merge qua PR.
- Commit theo dạng: `feat:`, `fix:`, `chore:`, `docs:`, `test:`.
- Mỗi PR cần ít nhất 1 người review và CI xanh.
'@
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
1. Client gọi `POST /solve` kèm JSON hoặc Excel.
2. API tạo job trong PostgreSQL và đẩy vào hàng đợi.
3. Worker lấy job, chạy CP-SAT, ghi kết quả vào DB và storage.
4. Client gọi `GET /jobs/{id}` để xem trạng thái và tải lịch.

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
from typing import Protocol


class JobRepositoryPort(Protocol):
    """Lưu trạng thái và kết quả job. Hiện thực: PostgreSQL (SQLAlchemy)."""
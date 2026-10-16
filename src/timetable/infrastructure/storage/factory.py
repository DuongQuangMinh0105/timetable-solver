import os
from pathlib import Path

from timetable.application.ports.storage import StoragePort


def create_storage() -> StoragePort:
    """Chọn nơi lưu file theo biến môi trường STORAGE_BACKEND.

    - `local` (mặc định): thư mục STORAGE_DIR (mặc định data/storage).
    - `postgres`: bảng `blobs` trong Postgres (DATABASE_URL), cho nơi không có ổ đĩa bền.

    API và worker phải dùng cùng một cấu hình để thấy cùng một nơi lưu file.
    """
    backend = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    if backend == "local":
        from timetable.infrastructure.storage.local import LocalStorage

        return LocalStorage(Path(os.getenv("STORAGE_DIR", "data/storage")))
    if backend == "postgres":
        # Import muộn: postgres.py kéo theo database.py, thứ cần DATABASE_URL ngay khi import.
        from timetable.infrastructure.storage.postgres import PostgresStorage

        return PostgresStorage()
    raise ValueError(f"STORAGE_BACKEND không hợp lệ: {backend!r} (dùng 'local' hoặc 'postgres')")

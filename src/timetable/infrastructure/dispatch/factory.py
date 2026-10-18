import os

from timetable.application.ports.job_dispatcher import JobDispatcherPort


def create_dispatcher() -> JobDispatcherPort:
    """Chọn cách giao job cho worker theo biến môi trường JOB_DISPATCHER.

    - `redis` (mặc định): đẩy job_id vào hàng đợi Redis, worker riêng đọc và xử lý.
    - `local`: API tự chạy worker như một tiến trình con (không cần Redis, không cần worker riêng).
      Dùng cho nơi không có Redis, ví dụ Render miễn phí.
    """
    backend = os.getenv("JOB_DISPATCHER", "redis").strip().lower()
    if backend == "redis":
        from timetable.infrastructure.dispatch.redis import RedisJobDispatcher

        return RedisJobDispatcher()
    if backend == "local":
        from timetable.infrastructure.dispatch.local import LocalJobDispatcher

        return LocalJobDispatcher()
    raise ValueError(f"JOB_DISPATCHER không hợp lệ: {backend!r} (dùng 'redis' hoặc 'local')")

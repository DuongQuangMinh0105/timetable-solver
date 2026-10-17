import os

from redis import Redis


class RedisJobDispatcher:
    """Đưa job_id vào Redis queue để worker xử lý bất đồng bộ."""

    def __init__(
        self,
        redis_url: str | None = None,
        queue_name: str = "timetable:jobs",
    ) -> None:
        self._redis = Redis.from_url(
            redis_url or os.environ.get("REDIS_URL") or "redis://localhost:6379/0",
            decode_responses=True,
        )
        self._queue_name = queue_name

    def dispatch(self, job_id: str) -> None:
        self._redis.lpush(self._queue_name, job_id)

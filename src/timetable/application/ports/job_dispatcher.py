from typing import Protocol


class JobDispatcherPort(Protocol):
    """Yêu cầu chạy một job giải theo job_id.

    Hiện thực: local (chạy worker cục bộ), Cloud Run Jobs, Container Apps Jobs.
    """

    def dispatch(self, job_id: str) -> None: ...

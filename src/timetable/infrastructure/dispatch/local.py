import os
import subprocess
import sys
from collections.abc import Sequence


class LocalJobDispatcher:
    """Hiện thực JobDispatcherPort: chạy worker cục bộ như một tiến trình riêng."""

    def __init__(self, command: Sequence[str] | None = None, *, wait: bool = False) -> None:
        self._command = (
            list(command) if command else [sys.executable, "-m", "timetable.interfaces.worker.main"]
        )
        self._wait = wait

    def dispatch(self, job_id: str) -> None:
        env = {**os.environ, "JOB_ID": job_id}
        if self._wait:
            subprocess.run(self._command, env=env, check=True)
        else:
            subprocess.Popen(self._command, env=env)

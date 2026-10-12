import subprocess
import sys
from pathlib import Path

import pytest

from timetable.application.ports.job_dispatcher import JobDispatcherPort
from timetable.infrastructure.dispatch.local import LocalJobDispatcher


def test_dispatch_passes_job_id(tmp_path: Path) -> None:
    out = tmp_path / "job_id.txt"
    script = f"import os, pathlib; pathlib.Path({str(out)!r}).write_text(os.environ['JOB_ID'])"
    dispatcher: JobDispatcherPort = LocalJobDispatcher([sys.executable, "-c", script], wait=True)
    dispatcher.dispatch("job-123")
    assert out.read_text() == "job-123"


def test_dispatch_failure_raises() -> None:
    dispatcher = LocalJobDispatcher([sys.executable, "-c", "raise SystemExit(1)"], wait=True)
    with pytest.raises(subprocess.CalledProcessError):
        dispatcher.dispatch("job-1")


def test_default_command_runs_worker_and_exits() -> None:
    LocalJobDispatcher(wait=True).dispatch("job-abc")

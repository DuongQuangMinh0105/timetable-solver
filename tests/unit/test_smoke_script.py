import json
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "smoke_test.py"


class _FakeApi(BaseHTTPRequestHandler):
    """API giả: hành vi chọn qua thuộc tính của lớp server."""

    def _send(self, status: int, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        config: dict[str, Any] = self.server.config  # type: ignore[attr-defined]
        if self.path == "/health":
            self._send(200, '{"status":"healthy"}')
        elif self.path.startswith("/jobs/"):
            statuses: list[str] = config["job_statuses"]
            status = statuses.pop(0) if len(statuses) > 1 else statuses[0]
            self._send(200, json.dumps({"job_id": "j1", "status": status, "result_ref": None}))
        else:
            self._send(404, '{"detail":"Not Found"}')

    def do_POST(self) -> None:
        config: dict[str, Any] = self.server.config  # type: ignore[attr-defined]
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/solve" and config["solve_status"] == 202:
            self._send(202, '{"job_id":"j1","status":"queued"}')
        else:
            self._send(config["solve_status"], "Internal Server Error")

    def log_message(self, *args: object) -> None:
        return


@pytest.fixture
def fake_api() -> Iterator[tuple[str, dict[str, Any]]]:
    server = HTTPServer(("127.0.0.1", 0), _FakeApi)
    config: dict[str, Any] = {"solve_status": 202, "job_statuses": ["RUNNING", "DONE"]}
    server.config = config  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", config
    server.shutdown()


def _run(base_url: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            base_url,
            "--wake-timeout",
            "3",
            "--timeout",
            "30",
            "--poll",
            "0.2",
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_smoke_test_passes_when_job_is_done(fake_api: tuple[str, dict[str, Any]]) -> None:
    result = _run(fake_api[0])

    assert result.returncode == 0, result.stderr
    assert "SMOKE TEST OK" in result.stdout


def test_smoke_test_fails_when_solve_returns_server_error(
    fake_api: tuple[str, dict[str, Any]],
) -> None:
    fake_api[1]["solve_status"] = 500  # đúng lỗi Render từng gặp: /solve trả Internal Server Error

    result = _run(fake_api[0])

    assert result.returncode == 1
    assert "HTTP 500" in result.stderr


def test_smoke_test_fails_when_job_fails(fake_api: tuple[str, dict[str, Any]]) -> None:
    fake_api[1]["job_statuses"] = ["RUNNING", "FAILED"]

    result = _run(fake_api[0])

    assert result.returncode == 1
    assert "FAILED" in result.stderr


def test_smoke_test_fails_when_service_is_unreachable() -> None:
    result = _run("http://127.0.0.1:1")

    assert result.returncode == 1
    assert "/health" in result.stderr

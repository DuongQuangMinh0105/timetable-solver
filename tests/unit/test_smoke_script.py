import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "smoke_test.py"
API_KEY = "khoa-thu-nghiem"
Fake = tuple[str, dict[str, Any]]


def _assignments(count: int) -> list[dict[str, Any]]:
    return [
        {"unit_id": f"U{i}", "day": 0, "start_period": i, "room_id": "R1"} for i in range(count)
    ]


class _FakeApi(BaseHTTPRequestHandler):
    """API giả: hành vi chọn qua thuộc tính `config` của server."""

    def _send(self, status: int, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _authorized(self) -> bool:
        return self.headers.get("X-API-Key") == self.server.config["api_key"]  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        config: dict[str, Any] = self.server.config  # type: ignore[attr-defined]
        if self.path == "/health":
            self._send(200, '{"status":"healthy"}')
        elif not self._authorized():
            self._send(401, '{"detail":"Invalid or missing API key"}')
        elif self.path.endswith("/result"):
            self._send(200, json.dumps(config["result"]))
        elif self.path.startswith("/jobs/"):
            statuses: list[str] = config["job_statuses"]
            status = statuses.pop(0) if len(statuses) > 1 else statuses[0]
            self._send(200, json.dumps({"job_id": "j1", "status": status, "result_ref": "r"}))
        else:
            self._send(404, '{"detail":"Not Found"}')

    def do_POST(self) -> None:
        config: dict[str, Any] = self.server.config  # type: ignore[attr-defined]
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if not self._authorized():
            self._send(401, '{"detail":"Invalid or missing API key"}')
        elif self.path == "/solve" and config["solve_status"] == 202:
            self._send(202, '{"job_id":"j1","status":"queued"}')
        else:
            self._send(config["solve_status"], "Internal Server Error")

    def log_message(self, *args: object) -> None:
        return


@pytest.fixture
def fake_api() -> Iterator[Fake]:
    server = HTTPServer(("127.0.0.1", 0), _FakeApi)
    config: dict[str, Any] = {
        "api_key": API_KEY,
        "solve_status": 202,
        "job_statuses": ["RUNNING", "DONE"],
        "result": {"status": "OPTIMAL", "objective": 0, "assignments": _assignments(2)},
    }
    server.config = config  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", config
    server.shutdown()


@pytest.fixture
def input_file(tmp_path: Path) -> Path:
    """Input giả có 2 ca học, khớp với kết quả mặc định của API giả."""
    path = tmp_path / "input.json"
    path.write_text(json.dumps({"lesson_units": [{"id": "U0"}, {"id": "U1"}]}), encoding="utf-8")
    return path


def _run(
    base_url: str, input_file: Path, api_key: str | None = API_KEY
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "API_KEY"}
    if api_key is not None:
        env["API_KEY"] = api_key
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            base_url,
            "--input",
            str(input_file),
            "--wake-timeout",
            "3",
            "--timeout",
            "30",
            "--poll",
            "0.2",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def test_passes_when_job_is_done_with_a_schedule(fake_api: Fake, input_file: Path) -> None:
    result = _run(fake_api[0], input_file)

    assert result.returncode == 0, result.stderr
    assert "OPTIMAL, 2 phân công" in result.stdout
    assert "SMOKE TEST OK" in result.stdout


def test_fails_when_solve_returns_server_error(fake_api: Fake, input_file: Path) -> None:
    fake_api[1]["solve_status"] = 500  # đúng lỗi Render từng gặp: /solve trả Internal Server Error

    result = _run(fake_api[0], input_file)

    assert result.returncode == 1
    assert "HTTP 500" in result.stderr


def test_fails_when_job_fails(fake_api: Fake, input_file: Path) -> None:
    fake_api[1]["job_statuses"] = ["RUNNING", "FAILED"]

    result = _run(fake_api[0], input_file)

    assert result.returncode == 1
    assert "FAILED" in result.stderr


def test_fails_when_service_is_unreachable(input_file: Path) -> None:
    result = _run("http://127.0.0.1:1", input_file)

    assert result.returncode == 1
    assert "/health" in result.stderr


def test_fails_without_api_key(fake_api: Fake, input_file: Path) -> None:
    result = _run(fake_api[0], input_file, api_key=None)

    assert result.returncode == 1
    assert "HTTP 401" in result.stderr
    assert "API_KEY" in result.stdout  # cảnh báo chưa đặt khóa


def test_fails_with_wrong_api_key(fake_api: Fake, input_file: Path) -> None:
    result = _run(fake_api[0], input_file, api_key="sai-khoa")

    assert result.returncode == 1
    assert "HTTP 401" in result.stderr


def test_fails_when_job_is_done_but_solver_timed_out(fake_api: Fake, input_file: Path) -> None:
    fake_api[1]["result"] = {"status": "UNKNOWN", "assignments": []}

    result = _run(fake_api[0], input_file)

    assert result.returncode == 1
    assert "UNKNOWN" in result.stderr


def test_fails_when_schedule_has_no_assignments(fake_api: Fake, input_file: Path) -> None:
    fake_api[1]["result"] = {"status": "FEASIBLE", "assignments": []}

    result = _run(fake_api[0], input_file)

    assert result.returncode == 1
    assert "không có phân công" in result.stderr


def test_fails_when_not_every_lesson_unit_is_assigned(fake_api: Fake, input_file: Path) -> None:
    fake_api[1]["result"] = {"status": "OPTIMAL", "assignments": _assignments(1)}

    result = _run(fake_api[0], input_file)

    assert result.returncode == 1
    assert "1 phân công, input có 2 ca học" in result.stderr


@pytest.mark.parametrize("url", ["", "   ", "khong-co-giao-thuc.example.com"])
def test_fails_cleanly_with_invalid_url(url: str, input_file: Path) -> None:
    result = _run(url, input_file)

    assert result.returncode == 1
    assert "địa chỉ dịch vụ không hợp lệ" in result.stderr
    assert "Traceback" not in result.stderr

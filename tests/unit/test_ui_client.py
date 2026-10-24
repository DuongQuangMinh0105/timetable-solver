import json
from typing import Any

import pytest

from timetable.interfaces.ui import client as client_module
from timetable.interfaces.ui.client import ApiError, SolverApiClient


class _Response:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_submit_sends_api_key_and_returns_job_id(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: float) -> _Response:
        seen["url"] = request.full_url
        seen["key"] = request.get_header("X-api-key")
        seen["method"] = request.get_method()
        return _Response({"status": "queued", "job_id": "abc"})

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    client = SolverApiClient("http://api:8000/", "secret")
    assert client.submit({"x": 1}) == "abc"
    assert seen == {"url": "http://api:8000/solve", "key": "secret", "method": "POST"}


def test_job_status_calls_the_job_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: Any, timeout: float) -> _Response:
        assert request.full_url == "http://api:8000/jobs/abc"
        return _Response({"job_id": "abc", "status": "DONE", "result_ref": "r"})

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    assert SolverApiClient("http://api:8000", "k").job_status("abc")["status"] == "DONE"


def test_unreachable_api_raises_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: Any, timeout: float) -> _Response:
        raise client_module.urllib.error.URLError("refused")

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ApiError, match="Không kết nối"):
        SolverApiClient("http://api:8000", "k").submit({})


def test_is_final() -> None:
    assert SolverApiClient.is_final("done")
    assert not SolverApiClient.is_final("QUEUED")


def test_timeout_becomes_a_friendly_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: Any, timeout: float) -> _Response:
        raise TimeoutError("The read operation timed out")

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ApiError, match="không phản hồi"):
        SolverApiClient("https://x.onrender.com", "k").submit({})


def test_timeout_is_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, float] = {}

    def fake_urlopen(request: Any, timeout: float) -> _Response:
        seen["timeout"] = timeout
        return _Response({"job_id": "abc"})

    monkeypatch.setenv("API_TIMEOUT_S", "200")
    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    SolverApiClient("http://api", "k").submit({})
    assert seen["timeout"] == 200.0


def test_job_result_calls_the_result_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: Any, timeout: float) -> _Response:
        assert request.full_url == "http://api:8000/jobs/abc/result"
        return _Response({"status": "INFEASIBLE", "assignments": [], "diagnosis": None})

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    assert SolverApiClient("http://api:8000", "k").job_result("abc")["status"] == "INFEASIBLE"

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_API_URL = "http://localhost:8000"
FINAL_STATUSES = {"DONE", "FAILED"}


class ApiError(RuntimeError):
    """API trả lỗi hoặc không kết nối được."""


class SolverApiClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        url = base_url or os.getenv("API_URL") or DEFAULT_API_URL
        self._base_url = url.rstrip("/")
        self._api_key = api_key if api_key is not None else os.getenv("API_KEY", "")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "X-API-Key": self._api_key},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ApiError(f"API trả mã {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ApiError(f"Không kết nối được API {self._base_url}: {exc.reason}") from exc

    def submit(self, payload: dict[str, Any]) -> str:
        return str(self._request("POST", "/solve", payload)["job_id"])

    def job_status(self, job_id: str) -> dict[str, Any]:
        result: dict[str, Any] = self._request("GET", f"/jobs/{job_id}")
        return result

    @staticmethod
    def is_final(status: str) -> bool:
        return status.upper() in FINAL_STATUSES

"""Smoke test cho staging: kiểm tra /health, gửi bài toán mẫu qua POST /solve, chờ job xong,
rồi đọc kết quả và kiểm tra có lịch hợp lệ.

Dùng:
    python scripts/smoke_test.py https://<địa-chỉ> [--input FILE] [--wake-timeout 120]
                                 [--timeout 300] [--poll 5]

Khóa API đọc từ biến môi trường API_KEY và gửi trong header X-API-Key (không ghi khóa vào lệnh).
Chỉ dùng thư viện chuẩn nên chạy được ở bất kỳ đâu (máy bạn, GitHub Actions).
Thoát với mã 0 nếu mọi thứ ổn, mã 1 nếu có lỗi.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Ép UTF-8 nếu stream hiện tại hỗ trợ reconfigure (ví dụ console Windows).
for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure) and stream.encoding != "utf-8":
        reconfigure(encoding="utf-8")

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "docs" / "schema" / "input.sample.json"
SUCCESS_STATUSES = {"DONE", "COMPLETED"}
FAILURE_STATUSES = {"FAILED", "ERROR"}
SCHEDULE_STATUSES = {"OPTIMAL", "FEASIBLE"}
DEFAULT_POLL_SECONDS = 5


class SmokeTestError(Exception):
    """Một bước của smoke test thất bại."""


def request(method: str, url: str, body: bytes | None = None) -> tuple[int, str]:
    """Gửi request, trả về (mã trạng thái, nội dung)."""
    req = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    api_key = os.environ.get("API_KEY", "")
    if api_key:
        req.add_header("X-API-Key", api_key)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        raise SmokeTestError(f"{method} {url}: {error}") from error


def wait_until_healthy(base_url: str, wake_timeout: float, poll: float) -> float:
    """Gọi /health cho tới khi dịch vụ phản hồi."""
    start = time.monotonic()
    last_error = "chưa có phản hồi"

    while time.monotonic() - start < wake_timeout:
        try:
            status, text = request("GET", f"{base_url}/health")
            if status == 200 and "healthy" in text:
                return time.monotonic() - start
            last_error = f"HTTP {status}: {text[:200]}"
        except SmokeTestError as error:
            last_error = str(error)

        time.sleep(poll)

    raise SmokeTestError(f"/health không sẵn sàng sau {wake_timeout:.0f}s ({last_error})")


def submit_job(base_url: str, payload: bytes) -> str:
    status, text = request("POST", f"{base_url}/solve", payload)
    if not 200 <= status < 300:
        raise SmokeTestError(f"POST /solve trả HTTP {status}: {text[:300]}")

    try:
        job_id = json.loads(text)["job_id"]
    except (ValueError, KeyError, TypeError) as error:
        raise SmokeTestError(f"POST /solve không trả job_id: {text[:300]}") from error

    return str(job_id)


def wait_for_job(base_url: str, job_id: str, timeout: float, poll: float) -> str:
    start = time.monotonic()
    last_status = ""

    while time.monotonic() - start < timeout:
        status, text = request("GET", f"{base_url}/jobs/{job_id}")
        if status != 200:
            raise SmokeTestError(f"GET /jobs/{job_id} trả HTTP {status}: {text[:300]}")

        job_status = str(json.loads(text).get("status", "")).upper()
        if job_status != last_status:
            print(f"  [{time.monotonic() - start:5.1f}s] job {job_status}")
            last_status = job_status

        if job_status in SUCCESS_STATUSES:
            return job_status
        if job_status in FAILURE_STATUSES:
            raise SmokeTestError(f"job {job_id} kết thúc với trạng thái {job_status}")

        time.sleep(poll)

    raise SmokeTestError(
        f"job {job_id} chưa xong sau {timeout:.0f}s (trạng thái cuối: {last_status})"
    )


def fetch_result(base_url: str, job_id: str) -> dict[str, Any]:
    status, text = request("GET", f"{base_url}/jobs/{job_id}/result")
    if status != 200:
        raise SmokeTestError(f"GET /jobs/{job_id}/result trả HTTP {status}: {text[:300]}")

    try:
        result = json.loads(text)
    except ValueError as error:
        raise SmokeTestError(f"kết quả không phải JSON: {text[:300]}") from error
    if not isinstance(result, dict):
        raise SmokeTestError(f"kết quả có dạng không mong đợi: {text[:300]}")

    return result


def check_result(result: dict[str, Any], expected_units: int) -> str:
    """Kiểm tra kết quả có lịch thật. Job DONE nhưng hết giờ giải (UNKNOWN) vẫn là lỗi."""
    status = str(result.get("status", "")).upper()
    if status not in SCHEDULE_STATUSES:
        raise SmokeTestError(f"kết quả có trạng thái {status or 'không rõ'}, không có lịch")

    assignments = result.get("assignments") or []
    if not assignments:
        raise SmokeTestError(f"kết quả {status} nhưng không có phân công nào")
    if expected_units and len(assignments) != expected_units:
        raise SmokeTestError(
            f"kết quả có {len(assignments)} phân công, input có {expected_units} ca học"
        )

    return f"{status}, {len(assignments)} phân công, điểm phạt {result.get('objective')}"


def run(
    base_url: str,
    input_path: Path,
    wake_timeout: float,
    timeout: float,
    poll: float,
) -> None:
    base_url = base_url.rstrip("/")
    print(f"Smoke test: {base_url}")
    if not os.environ.get("API_KEY"):
        print("Cảnh báo: chưa đặt biến môi trường API_KEY, các endpoint có khóa sẽ trả 401.")

    payload = input_path.read_bytes()
    expected_units = len(json.loads(payload).get("lesson_units") or [])

    woke_in = wait_until_healthy(base_url, wake_timeout, poll)
    print(f"1. /health ok sau {woke_in:.1f}s")

    start = time.monotonic()
    job_id = submit_job(base_url, payload)
    print(f"2. POST /solve nhận job {job_id}")

    wait_for_job(base_url, job_id, timeout, poll)
    print(f"3. Job xong sau {time.monotonic() - start:.1f}s")

    summary = check_result(fetch_result(base_url, job_id), expected_units)
    print(f"4. Kết quả: {summary}")
    print("SMOKE TEST OK")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "base_url",
        help="Địa chỉ dịch vụ, ví dụ https://timetable-solver.onrender.com",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="File input JSON gửi lên",
    )
    parser.add_argument(
        "--wake-timeout",
        type=float,
        default=120,
        help="Giây chờ /health (mặc định 120)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300,
        help="Giây chờ job xong (mặc định 300)",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=DEFAULT_POLL_SECONDS,
        help="Giây giữa các lần hỏi",
    )
    args = parser.parse_args()

    try:
        run(args.base_url, args.input, args.wake_timeout, args.timeout, args.poll)
    except SmokeTestError as error:
        print(f"SMOKE TEST THẤT BẠI: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

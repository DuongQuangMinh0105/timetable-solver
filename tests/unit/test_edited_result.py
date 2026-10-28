"""Kiểm tra, lưu và đọc kết quả đã sửa tay (use case và endpoint)."""

import json
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from timetable.application.use_cases.edited_result import (
    EditedResultNotFoundError,
    GetEditedResult,
    SaveEditedResult,
    ValidateEditedResult,
)
from timetable.application.use_cases.get_job import JobNotFoundError
from timetable.domain.entities.job import Job, JobStatus
from timetable.infrastructure.generator import generate_v1
from timetable.infrastructure.problem_loader import problem_from_dict
from timetable.infrastructure.solver.default_solver import build_default_solver
from timetable.interfaces.api import dependencies
from timetable.interfaces.api.main import app


class _Repo:
    def __init__(self, job: Job | None) -> None:
        self._job = job

    def get_by_id(self, job_id: Any) -> Job | None:
        return self._job


class _Storage:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    def get(self, key: str) -> bytes:
        return self.files[key]

    def put(self, key: str, data: bytes) -> None:
        self.files[key] = data

    def exists(self, key: str) -> bool:
        return key in self.files


@pytest.fixture(scope="module")
def solved() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Bài toán nhỏ cùng một lịch hợp lệ do solver tạo ra."""
    data = generate_v1(seed=3)
    problem = problem_from_dict(data)
    from timetable.application.dto.solve import SolveOptions

    result = build_default_solver(problem, data).solve(problem, SolveOptions(20, 1, 0))
    assert result.timetable is not None
    rows = [
        {"unit_id": a.unit_id, "day": a.day, "start_period": a.period, "room_id": a.room_id}
        for a in result.timetable.assignments
    ]
    return data, rows


def _setup(data: dict[str, Any]) -> tuple[Job, _Repo, _Storage]:
    job = Job(id=uuid4(), status=JobStatus.COMPLETED, input_ref="in.json", result_ref="r.json")
    storage = _Storage({"in.json": json.dumps(data).encode()})
    return job, _Repo(job), storage


def test_valid_schedule_has_no_hard_violations(solved: Any) -> None:
    data, rows = solved
    job, repo, storage = _setup(data)
    out = ValidateEditedResult(repo, storage, problem_from_dict).execute(job.id, rows)  # type: ignore[arg-type]
    assert out["summary"]["hard"] == 0


def test_moving_a_unit_onto_another_creates_hard_violations(solved: Any) -> None:
    data, rows = solved
    job, repo, storage = _setup(data)
    edited = [dict(r) for r in rows]
    edited[1].update(day=edited[0]["day"], start_period=edited[0]["start_period"])
    edited[1]["room_id"] = edited[0]["room_id"]  # cùng ô, cùng phòng: chắc chắn trùng phòng
    out = ValidateEditedResult(repo, storage, problem_from_dict).execute(job.id, edited)  # type: ignore[arg-type]
    assert out["summary"]["hard"] >= 1
    assert any(v["severity"] == "HARD" for v in out["violations"])


def test_missing_unit_is_reported(solved: Any) -> None:
    data, rows = solved
    job, repo, storage = _setup(data)
    out = ValidateEditedResult(repo, storage, problem_from_dict).execute(job.id, rows[1:])  # type: ignore[arg-type]
    assert out["summary"]["hard"] >= 1


def test_unknown_job_raises(solved: Any) -> None:
    data, rows = solved
    _job, _repo, storage = _setup(data)
    with pytest.raises(JobNotFoundError):
        ValidateEditedResult(_Repo(None), storage, problem_from_dict).execute(uuid4(), rows)  # type: ignore[arg-type]


def test_save_then_get_round_trip(solved: Any) -> None:
    data, rows = solved
    job, repo, storage = _setup(data)
    saved = SaveEditedResult(repo, storage, problem_from_dict).execute(job.id, rows)  # type: ignore[arg-type]
    assert saved["assignments"][0]["course_id"]  # dòng đầy đủ được dựng lại từ id ca học
    loaded = GetEditedResult(repo, storage).execute(job.id)  # type: ignore[arg-type]
    assert loaded == saved


def test_get_before_save_is_not_found(solved: Any) -> None:
    data, _rows = solved
    job, repo, storage = _setup(data)
    with pytest.raises(EditedResultNotFoundError):
        GetEditedResult(repo, storage).execute(job.id)  # type: ignore[arg-type]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, solved: Any) -> Any:
    monkeypatch.setenv("API_KEY", "k")
    data, _rows = solved
    job, repo, storage = _setup(data)
    app.dependency_overrides[dependencies.get_validate_edited_result] = lambda: (
        ValidateEditedResult(repo, storage, problem_from_dict)  # type: ignore[arg-type]
    )
    app.dependency_overrides[dependencies.get_save_edited_result] = lambda: SaveEditedResult(
        repo, storage, problem_from_dict
    )  # type: ignore[arg-type]
    app.dependency_overrides[dependencies.get_get_edited_result] = lambda: GetEditedResult(
        repo,  # type: ignore[arg-type]
        storage,
    )
    yield TestClient(app), job.id
    app.dependency_overrides.clear()


HEADERS = {"X-API-Key": "k"}


def test_api_validate_save_and_get(client: Any, solved: Any) -> None:
    http, job_id = client
    _data, rows = solved
    body = {"assignments": rows}
    url = f"/jobs/{job_id}"
    assert http.post(f"{url}/validate", json=body, headers=HEADERS).json()["summary"]["hard"] == 0
    assert http.get(f"{url}/result/edited", headers=HEADERS).status_code == 409
    saved = http.put(f"{url}/result/edited", json=body, headers=HEADERS)
    assert saved.status_code == 200
    got = http.get(f"{url}/result/edited", headers=HEADERS).json()
    assert got["assignments"] == saved.json()["assignments"]


def test_api_requires_key(client: Any) -> None:
    http, job_id = client
    assert http.post(f"/jobs/{job_id}/validate", json={"assignments": []}).status_code == 401
    assert http.get(f"/jobs/{job_id}/result/edited").status_code == 401


def test_api_rejects_bad_rows(client: Any) -> None:
    http, job_id = client
    bad = {"assignments": [{"unit_id": "u", "day": -1, "start_period": 0, "room_id": "R"}]}
    assert http.post(f"/jobs/{job_id}/validate", json=bad, headers=HEADERS).status_code == 422


def test_api_unknown_job_is_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "k")
    app.dependency_overrides[dependencies.get_validate_edited_result] = lambda: (
        ValidateEditedResult(_Repo(None), _Storage({}), problem_from_dict)  # type: ignore[arg-type]
    )
    try:
        url = f"/jobs/{UUID(int=1)}/validate"
        assert (
            TestClient(app).post(url, json={"assignments": []}, headers=HEADERS).status_code == 404
        )
    finally:
        app.dependency_overrides.clear()

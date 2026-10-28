"""Chạy giao diện Streamlit thật (AppTest) với API giả: sửa đầu vào, giải, kiểm tra, giải lại."""

from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from timetable.infrastructure.excel.importer import OpenpyxlExcelImporter
from timetable.interfaces.ui import client as client_module
from timetable.interfaces.ui.tables import payload_to_tables

APP = Path(__file__).resolve().parents[2] / "src/timetable/interfaces/ui/app.py"
SAMPLE = Path(__file__).resolve().parents[2] / "docs/samples/ok_basic.xlsx"

ASSIGNMENTS = [
    {"unit_id": "u1", "course_id": "C01", "class_id": "CS1", "teacher_id": "T1",
     "day": 0, "start_period": 0, "duration": 2, "room_id": "R101"},
    {"unit_id": "u2", "course_id": "C02", "class_id": "CS1", "teacher_id": "T2",
     "day": 1, "start_period": 2, "duration": 1, "room_id": "R102"},
]  # fmt: skip


class FakeApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any]] = []

    def __call__(self, _self: Any, method: str, path: str, body: Any = None) -> Any:
        self.calls.append((method, path, body))
        if path == "/solve":
            return {"job_id": "job1", "status": "queued"}
        if path.endswith("/validate"):
            return {
                "violations": [],
                "summary": {"hard": 0, "soft": 1, "soft_penalty": 10},
            }
        if path.endswith("/result/edited"):
            return {"violations": [], "summary": {"hard": 0, "soft": 0, "soft_penalty": 0},
                    "assignments": []}  # fmt: skip
        if path.endswith("/result"):
            return {"status": "OPTIMAL", "objective": 0, "assignments": ASSIGNMENTS,
                    "violations": [], "diagnosis": None}  # fmt: skip
        return {"job_id": "job1", "status": "DONE", "result_ref": "r"}

    def paths(self) -> list[str]:
        return [f"{m} {p}" for m, p, _ in self.calls]


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> FakeApi:
    fake = FakeApi()

    def patched(self: Any, method: str, path: str, body: Any = None) -> Any:
        return fake(self, method, path, body)

    monkeypatch.setattr(client_module.SolverApiClient, "_request", patched)
    return fake


def _app() -> AppTest:
    payload = OpenpyxlExcelImporter().load_data(SAMPLE)
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["draft"] = payload_to_tables(payload)
    at.session_state["base_payload"] = payload
    at.session_state["draft_version"] = 1
    return at


def _button(at: AppTest, label: str) -> Any:
    return next(b for b in at.button if b.label == label)


def test_input_tab_shows_editors_and_solves(api: FakeApi) -> None:
    at = _app().run()
    assert not at.exception
    _button(at, "💾 Lưu và giải").click().run()
    assert not at.exception
    assert api.paths()[:3] == ["POST /solve", "GET /jobs/job1", "GET /jobs/job1/result"]
    solved = api.calls[0][2]
    assert len(solved["courses"]) == 6 and "fixed_assignments" not in solved
    assert any(t.label == "✏️ Sửa kết quả" for t in at.tabs)


def test_check_edited_result_calls_validate(api: FakeApi) -> None:
    at = _app().run()
    _button(at, "💾 Lưu và giải").click().run()
    _button(at, "🔍 Kiểm tra").click().run()
    assert not at.exception
    method, path, body = next(c for c in api.calls if c[1].endswith("/validate"))
    assert (method, path) == ("POST", "/jobs/job1/validate")
    assert [r["unit_id"] for r in body["assignments"]] == ["u1", "u2"]
    assert set(body["assignments"][0]) == {"unit_id", "day", "start_period", "room_id"}


def test_save_edited_result_calls_put(api: FakeApi) -> None:
    at = _app().run()
    _button(at, "💾 Lưu và giải").click().run()
    _button(at, "💾 Lưu bản sửa").click().run()
    assert not at.exception
    assert "PUT /jobs/job1/result/edited" in api.paths()


def test_resolve_sends_fixed_assignments_list(api: FakeApi) -> None:
    at = _app().run()
    _button(at, "💾 Lưu và giải").click().run()
    _button(at, "🔁 Giải lại, giữ ca đã sửa/khóa").click().run()
    assert not at.exception
    solves = [c for c in api.calls if c[1] == "/solve"]
    assert len(solves) == 2
    assert solves[1][2]["fixed_assignments"] == []  # chưa sửa hay khóa ca nào


def test_invalid_input_is_reported_and_not_sent(api: FakeApi) -> None:
    at = _app()
    at.session_state["draft"]["courses"][0]["teacher_id"] = "KHONG_CO"
    at.run()
    _button(at, "💾 Lưu và giải").click().run()
    assert not at.exception
    assert not any(c[1] == "/solve" for c in api.calls)
    assert any("Dữ liệu chưa hợp lệ" in e.value for e in at.error)

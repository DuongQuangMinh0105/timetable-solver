import pytest
from fastapi.testclient import TestClient

from timetable.interfaces.api.main import app


def test_health_has_no_commit_outside_render(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_health_reports_deployed_commit_on_render(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER_GIT_COMMIT", "0123abc")

    response = TestClient(app).get("/health")

    assert response.json() == {"status": "healthy", "commit": "0123abc"}

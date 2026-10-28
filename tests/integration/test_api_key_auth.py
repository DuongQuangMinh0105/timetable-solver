from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from timetable.interfaces.api.dependencies import get_get_job, get_submit_solve_job
from timetable.interfaces.api.main import app

TEST_API_KEY = "test-api-key"


class FakeUseCase:
    """Track whether a protected endpoint reaches its use case."""

    def __init__(self) -> None:
        self.called = False

    def execute(self, *args: Any, **kwargs: Any) -> None:
        self.called = True
        raise AssertionError("Use case must not run for an unauthorized request")


def test_health_is_public(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("API_KEY", raising=False)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_solve_rejects_missing_api_key(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    fake = FakeUseCase()
    app.dependency_overrides[get_submit_solve_job] = lambda: fake

    try:
        with TestClient(app) as client:
            response = client.post("/solve", json={})

        assert response.status_code == 401
        assert fake.called is False
    finally:
        app.dependency_overrides.pop(get_submit_solve_job, None)


def test_solve_rejects_invalid_api_key(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    fake = FakeUseCase()
    app.dependency_overrides[get_submit_solve_job] = lambda: fake

    try:
        with TestClient(app) as client:
            response = client.post(
                "/solve",
                json={},
                headers={"X-API-Key": "wrong-key"},
            )

        assert response.status_code == 401
        assert fake.called is False
    finally:
        app.dependency_overrides.pop(get_submit_solve_job, None)


def test_get_job_rejects_missing_api_key(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    fake = FakeUseCase()
    app.dependency_overrides[get_get_job] = lambda: fake

    try:
        with TestClient(app) as client:
            response = client.get(f"/jobs/{uuid4()}")

        assert response.status_code == 401
        assert fake.called is False
    finally:
        app.dependency_overrides.pop(get_get_job, None)


def test_openapi_documents_api_key_header() -> None:
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    security_schemes = schema["components"]["securitySchemes"]
    assert "ApiKeyAuth" in security_schemes
    assert security_schemes["ApiKeyAuth"]["type"] == "apiKey"
    assert security_schemes["ApiKeyAuth"]["in"] == "header"
    assert security_schemes["ApiKeyAuth"]["name"] == "X-API-Key"

    assert schema["paths"]["/solve"]["post"]["security"]
    assert schema["paths"]["/jobs/{job_id}"]["get"]["security"]
    assert schema["paths"]["/jobs/{job_id}/result"]["get"]["security"]

    assert schema["paths"]["/jobs/{job_id}/validate"]["post"]["security"]
    assert schema["paths"]["/jobs/{job_id}/result/edited"]["put"]["security"]
    assert schema["paths"]["/jobs/{job_id}/result/edited"]["get"]["security"]
    assert "security" not in schema["paths"]["/health"]["get"]


def test_openapi_documents_api_operations_and_response_schemas() -> None:
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    operations = schema["paths"]
    assert set(operations) == {
        "/health",
        "/solve",
        "/jobs/{job_id}",
        "/jobs/{job_id}/result",
        "/jobs/{job_id}/validate",
        "/jobs/{job_id}/result/edited",
    }
    assert (
        operations["/solve"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/SolveRequest"
    )
    assert (
        operations["/solve"]["post"]["responses"]["202"]["content"]["application/json"]["schema"][
            "$ref"
        ]
        == "#/components/schemas/SolveAcceptedResponse"
    )
    assert (
        operations["/jobs/{job_id}"]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        == "#/components/schemas/JobResponse"
    )
    assert (
        operations["/jobs/{job_id}/result"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/JobResultResponse"
    )
    weight_schema = schema["components"]["schemas"]["SolveRequest"]["properties"]["soft_weights"]
    assert weight_schema["additionalProperties"]["type"] == "integer"
    assert weight_schema["additionalProperties"]["minimum"] == 0
    assert "nonnegative integer weights" in weight_schema["description"]
    assert set(operations["/solve"]["post"]["responses"]) >= {"202", "401", "422"}
    assert set(operations["/jobs/{job_id}"]["get"]["responses"]) >= {"200", "401", "404", "422"}
    assert set(operations["/jobs/{job_id}/result"]["get"]["responses"]) >= {
        "200",
        "401",
        "404",
        "409",
        "422",
    }

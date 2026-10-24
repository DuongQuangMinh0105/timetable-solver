from typing import Literal

from pydantic import BaseModel

SolveResultStatus = Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN", "MODEL_INVALID"]


class AssignmentResponse(BaseModel):
    unit_id: str
    course_id: str
    class_id: str
    teacher_id: str
    day: int
    start_period: int
    duration: int
    room_id: str


class ViolationResponse(BaseModel):
    rule_id: str
    description: str
    severity: str


class DiagnosisIssueResponse(BaseModel):
    code: str
    message: str
    suggestion: str


class DiagnosisResponse(BaseModel):
    """Lý do vô nghiệm (tiếng Việt): `source` là "precheck" hoặc "solver"."""

    source: str
    issues: list[DiagnosisIssueResponse]


class JobResultResponse(BaseModel):
    constraint_config_version: str
    status: SolveResultStatus
    objective: int | float | None
    cost_terms: dict[str, int]
    assignments: list[AssignmentResponse]
    violations: list[ViolationResponse]
    diagnosis: DiagnosisResponse | None = None

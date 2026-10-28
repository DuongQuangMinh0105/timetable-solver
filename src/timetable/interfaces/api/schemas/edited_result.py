from pydantic import BaseModel, Field

from timetable.interfaces.api.schemas.job_result_response import (
    AssignmentResponse,
    ViolationResponse,
)


class EditedAssignment(BaseModel):
    """Một dòng lịch do người dùng sửa; `start_period` là tiết bắt đầu (như kết quả giải)."""

    unit_id: str = Field(min_length=1)
    day: int = Field(ge=0)
    start_period: int = Field(ge=0)
    room_id: str = Field(min_length=1)


class EditedResultRequest(BaseModel):
    assignments: list[EditedAssignment]


class ValidationSummary(BaseModel):
    hard: int
    soft: int
    soft_penalty: int


class ValidateResponse(BaseModel):
    violations: list[ViolationResponse]
    summary: ValidationSummary


class EditedResultResponse(ValidateResponse):
    assignments: list[AssignmentResponse]

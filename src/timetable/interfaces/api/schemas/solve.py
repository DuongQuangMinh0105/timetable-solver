from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from timetable.application.dto.solve import SolveOptions


class InputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")


class GridInput(InputSchema):
    days: int = Field(gt=0)
    periods: int = Field(gt=0)
    allowed_periods: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_allowed_periods(self) -> Self:
        if self.allowed_periods != sorted(set(self.allowed_periods)):
            raise ValueError("allowed_periods phải tăng dần và không trùng")

        if any(period < 0 or period >= self.periods for period in self.allowed_periods):
            raise ValueError("allowed_periods có tiết nằm ngoài lưới")

        return self


class RoomInput(InputSchema):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    capacity: int = Field(gt=0)
    room_type: str = "standard"
    also_supports: list[str] = Field(default_factory=list)


class TeacherInput(InputSchema):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class ClassGroupInput(InputSchema):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    size: int = Field(gt=0)
    kind: str = "regular"


class CourseInput(InputSchema):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    class_id: str = Field(min_length=1)
    teacher_id: str = Field(min_length=1)
    periods_per_week: int = Field(gt=0)
    required_room_type: str = "standard"


class LessonUnitInput(InputSchema):
    id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    class_id: str = Field(min_length=1)
    teacher_id: str = Field(min_length=1)
    index: int = 0
    required_room_type: str = "standard"
    duration: int = Field(default=1, gt=0)


class ConstraintsInput(InputSchema):
    max_consecutive_periods: int = Field(default=2, gt=0)
    block_starts: list[int] | None = None


_DEFAULT_SOLVE_OPTIONS = SolveOptions()


class SolverInput(InputSchema):
    time_limit_s: float = Field(
        default=_DEFAULT_SOLVE_OPTIONS.time_limit_s,
        gt=0,
    )
    num_workers: int = Field(
        default=_DEFAULT_SOLVE_OPTIONS.num_workers,
        gt=0,
    )
    random_seed: int = _DEFAULT_SOLVE_OPTIONS.random_seed


class SolveRequest(InputSchema):
    schema_version: str = Field(min_length=1)
    grid: GridInput
    rooms: list[RoomInput] = Field(min_length=1)
    teachers: list[TeacherInput] = Field(min_length=1)
    class_groups: list[ClassGroupInput] = Field(min_length=1)
    courses: list[CourseInput] = Field(min_length=1)
    lesson_units: list[LessonUnitInput] = Field(default_factory=list)
    constraints: ConstraintsInput = Field(default_factory=ConstraintsInput)
    soft_weights: dict[str, int | float] = Field(default_factory=dict)
    solver: SolverInput = Field(default_factory=SolverInput)
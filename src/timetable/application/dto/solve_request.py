from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from timetable.application.dto.solve import SolveOptions
from timetable.domain.constraint_config import (
    SUPPORTED_CONSTRAINT_CONFIG_VERSIONS,
    unsupported_version_message,
)
from timetable.domain.rules.soft_constraints import SOFT_WEIGHT_KEYS

NonNegativeStrictInt = Annotated[int, Field(strict=True, ge=0)]


class InputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")


class GridInput(InputSchema):
    days: int = Field(gt=0)
    periods: int = Field(gt=0)
    allowed_periods: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_allowed_periods(self) -> Self:
        if self.allowed_periods != sorted(set(self.allowed_periods)):
            raise ValueError("allowed_periods pháº£i tÄƒng dáº§n vÃ  khÃ´ng trÃ¹ng")

        if any(period < 0 or period >= self.periods for period in self.allowed_periods):
            raise ValueError("allowed_periods cÃ³ tiáº¿t náº±m ngoÃ i lÆ°á»›i")

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
    department: str | None = None


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
    department: str | None = None


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


class FixedAssignmentInput(InputSchema):
    """Một ca bị khóa vào ô cố định. `start_period` là tiết bắt đầu (như trong kết quả giải)."""

    unit_id: str = Field(min_length=1)
    day: int = Field(ge=0)
    start_period: int = Field(ge=0)
    room_id: str = Field(min_length=1)


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
    constraint_config_version: str | None = None
    grid: GridInput
    rooms: list[RoomInput] = Field(min_length=1)
    teachers: list[TeacherInput] = Field(min_length=1)
    class_groups: list[ClassGroupInput] = Field(min_length=1)
    courses: list[CourseInput] = Field(min_length=1)
    lesson_units: list[LessonUnitInput] = Field(default_factory=list)
    constraints: ConstraintsInput = Field(default_factory=ConstraintsInput)
    soft_weights: dict[str, NonNegativeStrictInt] = Field(
        default_factory=dict,
        description=(
            "Optional nonnegative integer weights for room_stability, avoid_saturday, and "
            "reserve_mba_room."
        ),
    )
    fixed_assignments: list[FixedAssignmentInput] = Field(default_factory=list)
    solver: SolverInput = Field(default_factory=SolverInput)

    @field_validator("soft_weights")
    @classmethod
    def validate_soft_weights(cls, weights: dict[str, int]) -> dict[str, int]:
        unsupported = set(weights) - SOFT_WEIGHT_KEYS
        if unsupported:
            raise ValueError(f"Unsupported soft_weights keys: {sorted(unsupported)}")
        return weights

    @model_validator(mode="after")
    def validate_constraint_config_version(self) -> Self:
        version = self.constraint_config_version
        if version is not None and version not in SUPPORTED_CONSTRAINT_CONFIG_VERSIONS:
            raise ValueError(unsupported_version_message(version))
        return self

    @model_validator(mode="after")
    def validate_entity_references(self) -> Self:
        collections = (
            ("rooms", self.rooms),
            ("teachers", self.teachers),
            ("class_groups", self.class_groups),
            ("courses", self.courses),
            ("lesson_units", self.lesson_units),
        )
        for name, entities in collections:
            identifiers = [entity.id for entity in entities]
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"{name} ids must be unique")

        class_ids = {class_group.id for class_group in self.class_groups}
        teacher_ids = {teacher.id for teacher in self.teachers}
        courses = {course.id: course for course in self.courses}

        for course in self.courses:
            if course.class_id not in class_ids:
                raise ValueError(f"Course {course.id} references unknown class {course.class_id}")
            if course.teacher_id not in teacher_ids:
                raise ValueError(
                    f"Course {course.id} references unknown teacher {course.teacher_id}"
                )

        if not self.lesson_units:
            return self

        total_by_course = dict.fromkeys(courses, 0)
        for unit in self.lesson_units:
            unit_course = courses.get(unit.course_id)
            if unit_course is None:
                raise ValueError(
                    f"Lesson unit {unit.id} references unknown course {unit.course_id}"
                )
            if unit.class_id not in class_ids:
                raise ValueError(f"Lesson unit {unit.id} references unknown class {unit.class_id}")
            if unit.teacher_id not in teacher_ids:
                raise ValueError(
                    f"Lesson unit {unit.id} references unknown teacher {unit.teacher_id}"
                )
            if (
                unit.class_id != unit_course.class_id
                or unit.teacher_id != unit_course.teacher_id
                or unit.required_room_type != unit_course.required_room_type
            ):
                raise ValueError(f"Lesson unit {unit.id} does not match course {unit_course.id}")
            if unit.duration not in (1, 2):
                raise ValueError(f"Lesson unit {unit.id} duration must be 1 or 2")
            total_by_course[unit_course.id] += unit.duration

        for course in self.courses:
            if total_by_course[course.id] != course.periods_per_week:
                raise ValueError(
                    f"Course {course.id} requires {course.periods_per_week} periods but its "
                    f"lesson units total {total_by_course[course.id]}"
                )

        return self

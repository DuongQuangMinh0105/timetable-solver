import json
from pathlib import Path

import pytest

from timetable.domain.entities import (
    ClassGroup,
    Course,
    LessonUnit,
    Problem,
    Room,
    Teacher,
    TimeGrid,
)

SAMPLE_PATH = Path(__file__).resolve().parents[1] / "docs" / "schema" / "input.sample.json"


def load_problem(path: Path) -> Problem:
    data = json.loads(path.read_text(encoding="utf-8"))
    grid = data["grid"]
    return Problem(
        rooms=tuple(
            Room(
                id=r["id"],
                name=r["name"],
                capacity=r["capacity"],
                room_type=r["room_type"],
                also_supports=tuple(r["also_supports"]),
            )
            for r in data["rooms"]
        ),
        teachers=tuple(Teacher(**t) for t in data["teachers"]),
        class_groups=tuple(ClassGroup(**c) for c in data["class_groups"]),
        courses=tuple(Course(**c) for c in data["courses"]),
        lesson_units=tuple(LessonUnit(**u) for u in data["lesson_units"]),
        grid=TimeGrid(
            days=grid["days"],
            periods=grid["periods"],
            allowed_periods=tuple(grid["allowed_periods"]),
        ),
        max_consecutive_periods=data["constraints"]["max_consecutive_periods"],
    )


@pytest.fixture
def sample_problem() -> Problem:
    return load_problem(SAMPLE_PATH)

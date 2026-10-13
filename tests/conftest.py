from pathlib import Path

import pytest

from timetable.domain.entities import Problem
from timetable.infrastructure.problem_loader import load_problem

SAMPLE_PATH = Path(__file__).resolve().parents[1] / "docs" / "schema" / "input.sample.json"


@pytest.fixture
def sample_problem() -> Problem:
    return load_problem(SAMPLE_PATH)

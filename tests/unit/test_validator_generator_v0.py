from timetable.domain.validator import Validator
from timetable.infrastructure.generator import generate_v0


def test_validator_empty_timetable() -> None:
    validator = Validator()
    violations = validator.validate(timetable=None, rules=[])
    assert len(violations) == 1
    assert violations[0].rule_id == "TIMETABLE_EMPTY"


def test_generator_v0_success() -> None:
    data = generate_v0(num_rooms=4, num_teachers=6)
    assert len(data["rooms"]) == 4
    assert len(data["teachers"]) == 6
    assert data["rooms"][0] == "Room_01"
    assert data["teachers"][0] == "Teacher_01"
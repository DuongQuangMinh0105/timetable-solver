from timetable.domain.validator import Validator


def test_validator_mba_room_pass_and_fail() -> None:
    validator = Validator()

    # Trường hợp Pass: MBA đúng phòng G316
    valid_timetable = [
        {"period": 1, "room": "G316", "teacher": "T1", "class_group": "C1", "subject": "MBA"}
    ]
    assert len(validator.validate(valid_timetable)) == 0

    # Trường hợp Fail: MBA sai phòng (ở G101)
    invalid_timetable = [
        {"period": 1, "room": "G101", "teacher": "T1", "class_group": "C1", "subject": "MBA"}
    ]
    violations = validator.validate(invalid_timetable)
    assert any(v.rule_id == "MBA_ROOM_VIOLATION" for v in violations)


def test_validator_drawing_room_pass_and_fail() -> None:
    validator = Validator()

    # Trường hợp Pass: Lớp vẽ đúng phòng G313
    valid_timetable = [
        {"period": 2, "room": "G313", "teacher": "T2", "class_group": "C2", "subject": "Môn Vẽ"}
    ]
    assert len(validator.validate(valid_timetable)) == 0

    # Trường hợp Fail: Lớp vẽ sai phòng (ở G202)
    invalid_timetable = [
        {"period": 2, "room": "G202", "teacher": "T2", "class_group": "C2", "subject": "Drawing"}
    ]
    violations = validator.validate(invalid_timetable)
    assert any(v.rule_id == "DRAWING_ROOM_VIOLATION" for v in violations)


def test_validator_max_consecutive_pass_and_fail() -> None:
    validator = Validator()

    # Trường hợp Pass: Học 2 tiết liên tiếp (tiết 1, 2)
    valid_timetable = [
        {"period": 1, "room": "G101", "teacher": "T1", "class_group": "C1"},
        {"period": 2, "room": "G101", "teacher": "T1", "class_group": "C1"},
    ]
    assert len(validator.validate(valid_timetable)) == 0

    # Trường hợp Fail: Học 3 tiết liên tiếp (tiết 1, 2, 3)
    invalid_timetable = [
        {"period": 1, "room": "G101", "teacher": "T1", "class_group": "C1"},
        {"period": 2, "room": "G101", "teacher": "T1", "class_group": "C1"},
        {"period": 3, "room": "G101", "teacher": "T1", "class_group": "C1"},
    ]
    violations = validator.validate(invalid_timetable)
    assert any(v.rule_id == "MAX_CONSECUTIVE" for v in violations)

from timetable.interfaces.ui.diagnosis_view import (
    FALLBACK_TITLE,
    TIMEOUT_TITLE,
    diagnosis_lines,
    diagnosis_title,
    needs_diagnosis,
)

INFEASIBLE = {
    "status": "INFEASIBLE",
    "assignments": [],
    "diagnosis": {
        "source": "precheck",
        "issues": [
            {
                "code": "teacher_capacity",
                "message": "Giáo viên T1 quá tải.",
                "suggestion": "Thêm GV.",
            }
        ],
    },
}


def test_lines_contain_message_and_suggestion() -> None:
    (line,) = diagnosis_lines(INFEASIBLE)
    assert "Giáo viên T1 quá tải." in line and "Thêm GV." in line


def test_title_depends_on_source() -> None:
    assert "trước khi giải" in diagnosis_title(INFEASIBLE)
    assert diagnosis_title({"status": "INFEASIBLE"}) == FALLBACK_TITLE


def test_no_diagnosis_gives_no_lines() -> None:
    assert diagnosis_lines({"status": "INFEASIBLE", "diagnosis": None}) == []
    assert diagnosis_lines({"status": "OPTIMAL"}) == []


def test_needs_diagnosis_only_without_schedule() -> None:
    assert needs_diagnosis(INFEASIBLE)
    assert needs_diagnosis({"status": "UNKNOWN", "assignments": []})
    assert not needs_diagnosis({"status": "OPTIMAL", "assignments": [{"unit_id": "u"}]})


def test_unknown_without_diagnosis_is_a_timeout_not_infeasible() -> None:
    assert diagnosis_title({"status": "UNKNOWN"}) == TIMEOUT_TITLE
    assert "vô nghiệm" not in TIMEOUT_TITLE

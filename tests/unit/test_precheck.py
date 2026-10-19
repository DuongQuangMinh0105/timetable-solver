
from timetable.domain.services.precheck import Issue, OfferingInfo, precheck


def _o(
    id: str,
    kind: str = "regular",
    size: int = 25,
    sessions: int = 2,
    teacher: str = "T1",
) -> OfferingInfo:
    return OfferingInfo(id, kind, size, sessions, teacher)


def codes(issues: list[Issue]) -> set[str]:
    return {issue.code for issue in issues}


def test_valid_input_has_no_issue() -> None:
    assert precheck([_o("A"), _o("B", teacher="T2")], regular_room_count=5) == []


def test_class_size_out_of_range() -> None:
    assert "class_size" in codes(precheck([_o("A", size=35)], regular_room_count=5))
    assert "class_size" in codes(precheck([_o("A", size=15)], regular_room_count=5))


def test_teacher_overload() -> None:
    offerings = [_o(f"X{i}", sessions=10) for i in range(2)]  # 20 > 18
    assert "teacher_overload" in codes(precheck(offerings, regular_room_count=5))


def test_mba_capacity() -> None:
    offerings = [_o(f"M{i}", "mba", sessions=10, teacher=f"T{i}") for i in range(2)]
    assert "mba_capacity" in codes(precheck(offerings, regular_room_count=5))


def test_design_capacity() -> None:
    offerings = [_o(f"D{i}", "design", sessions=10, teacher=f"T{i}") for i in range(2)]
    assert "design_capacity" in codes(precheck(offerings, regular_room_count=5))


def test_total_capacity() -> None:
    offerings = [_o(f"X{i}", sessions=18, teacher=f"T{i}") for i in range(3)]  # 54 > 18
    assert "total_capacity" in codes(precheck(offerings, regular_room_count=2))

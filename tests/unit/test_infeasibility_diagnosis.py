"""Test chẩn đoán vô nghiệm (infeasibility diagnosis).

Bao gồm các test cho precheck (kiểm tra trước khi gọi solver) và
các test cho solver groups (các nhóm ràng buộc bị xung đột).
"""

from timetable.application.use_cases.diagnose_infeasibility import DiagnoseInfeasibility
from timetable.domain.services.precheck import OfferingInfo


class FakeDiagnoser:
    def __init__(self, groups: list[str]):
        self._groups = groups
        self.called = False

    def conflicting_groups(self) -> list[str]:
        self.called = True
        return self._groups


# --- Precheck tests (kiểm tra dữ liệu đầu vào trước khi gọi solver) ---


def test_precheck_room_capacity_too_small():
    """Phòng học không đủ sức chứa."""
    offerings = [OfferingInfo("A", "regular", 100, 2, "T1")]  # 100 > sức chứa mặc định 30
    fake = FakeDiagnoser([])
    report = DiagnoseInfeasibility(fake).execute(offerings, regular_room_count=5)
    assert report.source == "precheck"
    assert not fake.called


def test_precheck_too_many_students_for_room():
    """Tổng số sinh viên vượt quá sức chứa của tất cả phòng."""
    offerings = [OfferingInfo(f"L{i}", "regular", 30, 2, "T1") for i in range(10)]  # 10*30=300
    fake = FakeDiagnoser([])
    report = DiagnoseInfeasibility(fake).execute(offerings, regular_room_count=5)  # 5*30=150
    assert report.source == "precheck"


def test_precheck_design_room_overload():
    """Quá nhiều lớp Design cho 1 phòng G313 (2 lớp x 20 tiết = 40 > 36)."""
    offerings = [
        OfferingInfo("D1", "design", 20, 20, "T1"),  # periods_per_week=20
        OfferingInfo("D2", "design", 20, 20, "T2"),  # periods_per_week=20
    ]
    fake = FakeDiagnoser([])
    report = DiagnoseInfeasibility(fake).execute(
        offerings, regular_room_count=5, design_room_count=1
    )
    assert report.source == "precheck"
    assert any("design_room_overload" in i.code for i in report.issues)


def test_solver_mba_room_missing():
    """Solver phát hiện thiếu phòng MBA (G316)."""
    offerings = [OfferingInfo("A", "mba", 20, 2, "T1")]
    fake = FakeDiagnoser(["mba_room"])  # Giả lập solver báo lỗi mba_room
    report = DiagnoseInfeasibility(fake).execute(
        offerings, regular_room_count=5, design_room_count=1
    )
    assert report.source == "solver"
    assert "mba_room" in [i.code for i in report.issues]


# --- Solver groups tests (các nhóm ràng buộc bị xung đột) ---


def test_solver_each_unit_once():
    """Mỗi unit phải được xếp đúng một lần."""
    fake = FakeDiagnoser(["each_unit_once"])
    report = DiagnoseInfeasibility(fake).execute([], 5)
    assert report.source == "solver"
    assert "unit" in report.issues[0].message.lower()


def test_solver_room_no_overlap():
    """Không đủ phòng để tránh trùng lịch."""
    fake = FakeDiagnoser(["room_no_overlap"])
    report = DiagnoseInfeasibility(fake).execute([], 5)
    assert report.source == "solver"
    assert "phòng" in report.issues[0].message.lower()


def test_solver_teacher_no_overlap():
    """Giáo viên bị trùng lịch."""
    fake = FakeDiagnoser(["teacher_no_overlap"])
    report = DiagnoseInfeasibility(fake).execute([], 5)
    assert report.source == "solver"
    assert "giáo viên" in report.issues[0].message.lower()


def test_solver_class_no_overlap():
    """Lớp bị trùng lịch."""
    fake = FakeDiagnoser(["class_no_overlap"])
    report = DiagnoseInfeasibility(fake).execute([], 5)
    assert report.source == "solver"
    assert "lớp" in report.issues[0].message.lower()


def test_solver_max_consecutive_periods():
    """Vi phạm giới hạn tiết liên tiếp."""
    fake = FakeDiagnoser(["max_consecutive_periods"])
    report = DiagnoseInfeasibility(fake).execute([], 5)
    assert report.source == "solver"
    assert "liên tiếp" in report.issues[0].message.lower()


def test_solver_unknown_group():
    """Nhóm lỗi không xác định."""
    fake = FakeDiagnoser(["unknown_group"])
    report = DiagnoseInfeasibility(fake).execute([], 5)
    assert report.source == "solver"
    assert "unknown_group" in report.issues[0].message


def test_solver_multiple_groups():
    """Nhiều nhóm lỗi cùng lúc."""
    fake = FakeDiagnoser(["room_no_overlap", "teacher_no_overlap"])
    report = DiagnoseInfeasibility(fake).execute([], 5)
    assert report.source == "solver"
    assert len(report.issues) == 2


def test_no_issues():
    """Không có lỗi nào."""
    fake = FakeDiagnoser([])
    report = DiagnoseInfeasibility(fake).execute([], 5)
    assert report.source == "none"
    assert not report.has_issues


# --- Test tích hợp precheck + solver ---


def test_precheck_passes_then_solver_finds_issue():
    """Precheck pass nhưng solver phát hiện lỗi."""
    offerings = [OfferingInfo("A", "regular", 20, 2, "T1")]
    fake = FakeDiagnoser(["room_no_overlap"])
    report = DiagnoseInfeasibility(fake).execute(offerings, 5)
    assert report.source == "solver"
    assert fake.called


def test_precheck_fails_skips_solver():
    """Precheck fail, không gọi solver."""
    offerings = [OfferingInfo("A", "regular", 100, 2, "T1")]
    fake = FakeDiagnoser(["room_no_overlap"])
    report = DiagnoseInfeasibility(fake).execute(offerings, 5)
    assert report.source == "precheck"
    assert not fake.called

import sys
from pathlib import Path

# Thêm thư mục tests/unit vào sys.path để Python nhận diện được excel_helpers
sys.path.append(str(Path(__file__).parent.parent / "unit"))

from excel_helpers import sheets_from_data, write_workbook

from timetable.application.dto.solve import SolveOptions, SolveStatus
from timetable.domain.services.validation_report import build_report
from timetable.infrastructure.excel.importer import OpenpyxlExcelImporter
from timetable.infrastructure.generator import generate_v1
from timetable.infrastructure.solver.default_solver import build_default_solver


# --- Checklist Ràng buộc: Case PASS ---
def test_acceptance_checklist_pass(tmp_path: Path) -> None:
    """Test chấp nhận PASS: Dữ liệu chuẩn từ generator phải đạt 0 vi phạm."""
    data = generate_v1()
    source = write_workbook(tmp_path / "in_pass.xlsx", sheets_from_data(data))

    problem = OpenpyxlExcelImporter().load(source)
    solver = build_default_solver(problem, data)
    result = solver.solve(problem, SolveOptions(time_limit_s=20, num_workers=2))

    assert result.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
    assert result.timetable is not None

    report = build_report(problem, result.timetable)
    assert report.summary()["hard"] == 0


# --- Checklist Ràng buộc: Case FAIL ---
def test_acceptance_checklist_fail(tmp_path: Path) -> None:
    """Test chấp nhận FAIL: Kiểm tra hệ thống ghi nhận và báo cáo lỗi

    khi dữ liệu hoặc ràng buộc không thỏa mãn.
    """
    data = generate_v1()
    source = write_workbook(tmp_path / "in_fail.xlsx", sheets_from_data(data))

    problem = OpenpyxlExcelImporter().load(source)
    solver = build_default_solver(problem, data)
    result = solver.solve(problem, SolveOptions(time_limit_s=20, num_workers=2))

    assert result.timetable is not None

    report = build_report(problem, result.timetable)
    assert isinstance(report.summary(), dict)
    assert "hard" in report.summary()

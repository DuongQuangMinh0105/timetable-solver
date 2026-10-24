from pathlib import Path

import pytest
from excel_helpers import Sheets, sheets_from_data, write_workbook

from timetable.application.ports.excel_importer import ExcelImportError
from timetable.infrastructure.excel.importer import OpenpyxlExcelImporter
from timetable.infrastructure.generator import generate_v1


def _valid() -> Sheets:
    return sheets_from_data(generate_v1())


def _load(tmp_path: Path, sheets: Sheets):  # type: ignore[no-untyped-def]
    return OpenpyxlExcelImporter().load(write_workbook(tmp_path / "in.xlsx", sheets))


def test_valid_file_gives_the_expected_problem(tmp_path: Path) -> None:
    data = generate_v1()
    problem = _load(tmp_path, _valid())
    assert len(problem.rooms) == len(data["rooms"])
    assert len(problem.teachers) == len(data["teachers"])
    assert len(problem.class_groups) == len(data["class_groups"])
    assert len(problem.courses) == len(data["courses"])


def test_missing_sheet_is_reported(tmp_path: Path) -> None:
    sheets = _valid()
    del sheets["Lớp"]
    with pytest.raises(ExcelImportError, match="Thiếu sheet 'Lớp'"):
        _load(tmp_path, sheets)


def test_missing_column_is_reported(tmp_path: Path) -> None:
    sheets = _valid()
    sheets["Giáo viên"][0] = ["id"]
    with pytest.raises(ExcelImportError, match="Sheet Giáo viên, dòng 1: thiếu cột name"):
        _load(tmp_path, sheets)


def test_text_class_size_reports_sheet_and_row(tmp_path: Path) -> None:
    sheets = _valid()
    sheets["Lớp"][2][2] = "abc"  # dòng Excel số 3, cột size
    with pytest.raises(ExcelImportError, match="Sheet Lớp, dòng 3: cột size"):
        _load(tmp_path, sheets)


def test_duplicate_teacher_id_reports_row(tmp_path: Path) -> None:
    sheets = _valid()
    sheets["Giáo viên"].append(list(sheets["Giáo viên"][1]))
    row = len(sheets["Giáo viên"])
    with pytest.raises(ExcelImportError, match=f"Sheet Giáo viên, dòng {row}: trùng id"):
        _load(tmp_path, sheets)


def test_unknown_teacher_reference_is_reported(tmp_path: Path) -> None:
    sheets = _valid()
    sheets["Môn"][1][3] = "T99"
    with pytest.raises(ExcelImportError, match="Sheet Môn, dòng 2: giáo viên 'T99'"):
        _load(tmp_path, sheets)


def test_not_an_excel_file_is_reported(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xlsx"
    bad.write_text("không phải excel", encoding="utf-8")
    with pytest.raises(ExcelImportError, match="Không đọc được"):
        OpenpyxlExcelImporter().load(bad)


def test_load_data_gives_json_ready_dict(tmp_path: Path) -> None:
    path = write_workbook(tmp_path / "in.xlsx", _valid())
    data = OpenpyxlExcelImporter().load_data(path)
    assert data["schema_version"]
    assert len(data["rooms"]) == len(generate_v1()["rooms"])

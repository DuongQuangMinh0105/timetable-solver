"""Bốn file mẫu lỗi và một file hợp lệ theo mẫu Excel tiếng Anh (docs/samples)."""

import json
from pathlib import Path

import pytest

from timetable.application.dto.solve import SolveStatus
from timetable.application.ports.excel_importer import ExcelImportError
from timetable.domain.services.timetable_checker import check_timetable
from timetable.infrastructure.excel.importer import OpenpyxlExcelImporter
from timetable.infrastructure.solver.default_solver import build_default_solver
from timetable.infrastructure.solver.solve_handler import make_solve_handler

SAMPLES = Path(__file__).resolve().parents[2] / "docs" / "samples"


def _solve(name: str) -> dict:  # type: ignore[type-arg]
    data = OpenpyxlExcelImporter().load_data(SAMPLES / name)
    data["solver"] = {"time_limit_s": 20, "num_workers": 1, "random_seed": 0}
    handler = make_solve_handler(build_default_solver, check_timetable)
    return json.loads(handler(json.dumps(data).encode("utf-8")))  # type: ignore[no-any-return]


def test_valid_sample_is_scheduled_without_violations() -> None:
    result = _solve("ok_basic.xlsx")
    assert result["status"] in {SolveStatus.OPTIMAL, SolveStatus.FEASIBLE}
    assert result["violations"] == []
    assert result["diagnosis"] is None
    assert result["assignments"]


def test_importer_warns_about_columns_not_applied() -> None:
    importer = OpenpyxlExcelImporter()
    importer.load_data(SAMPLES / "ok_basic.xlsx")
    assert any("unavailable_slots" in w for w in importer.warnings)


def test_teacher_overload_is_diagnosed_before_solving() -> None:
    result = _solve("fail_teacher_overload.xlsx")
    assert result["status"] == "INFEASIBLE"
    assert result["diagnosis"]["source"] == "precheck"
    codes = {i["code"] for i in result["diagnosis"]["issues"]}
    assert "teacher_capacity" in codes
    message = next(
        i["message"] for i in result["diagnosis"]["issues"] if i["code"] == "teacher_capacity"
    )
    assert "T1" in message


def test_room_shortage_is_diagnosed() -> None:
    result = _solve("fail_room_shortage.xlsx")
    assert result["status"] == "INFEASIBLE"
    issue = result["diagnosis"]["issues"][0]
    assert issue["code"] == "room_capacity"
    assert "R101" in issue["message"]


def test_mba_without_special_room_is_diagnosed() -> None:
    result = _solve("fail_mba_no_special_room.xlsx")
    assert result["status"] == "INFEASIBLE"
    issue = result["diagnosis"]["issues"][0]
    assert issue["code"] == "no_valid_room"
    assert "C05" in issue["message"] and "C06" in issue["message"]


def test_period_out_of_range_is_an_import_error() -> None:
    with pytest.raises(ExcelImportError, match="tiết 9, ngoài khoảng tiết hợp lệ 1..6"):
        OpenpyxlExcelImporter().load_data(SAMPLES / "fail_period_out_of_range.xlsx")

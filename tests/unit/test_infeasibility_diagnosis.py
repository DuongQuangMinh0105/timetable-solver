"""Chẩn đoán vô nghiệm: cố tình tạo mâu thuẫn rồi kiểm tra nhóm xung đột được báo đúng."""

import json

from solver_helpers import ONE_SLOT, OPTIONS, make_problem, solve, unit
from timetable.application.dto.solve import SolveResult, SolveStatus
from timetable.application.use_cases.describe_conflicts import (
    MAX_OWNERS_SHOWN,
    describe_conflict_groups,
)
from timetable.application.use_cases.solve_timetable import SolveTimetable
from timetable.domain.entities import Problem
from timetable.domain.services.capacity_precheck import capacity_issues
from timetable.domain.services.precheck import Issue
from timetable.domain.services.timetable_checker import check_timetable
from timetable.infrastructure.generator import generate_hard
from timetable.infrastructure.solver.cpsat_solver import CpSatSolver
from timetable.infrastructure.solver.default_solver import build_default_solver
from timetable.infrastructure.solver.solve_handler import make_solve_handler


def _groups(problem: Problem) -> tuple[str, ...]:
    result = solve(problem)
    assert result.status == SolveStatus.INFEASIBLE
    return result.conflict_groups


def test_teacher_clash_is_reported():
    # Một giáo viên dạy hai lớp trong cùng một tiết duy nhất.
    groups = _groups(make_problem([unit("u1", "C1", "T1"), unit("u2", "C2", "T1")]))
    assert "teacher_no_overlap:T1" in groups


def test_class_clash_is_reported():
    groups = _groups(make_problem([unit("u1", "C1", "T1"), unit("u2", "C1", "T2")]))
    assert "class_no_overlap:C1" in groups


def test_room_clash_is_reported():
    # 4 ca học khác lớp, khác giáo viên nhưng chỉ có 3 phòng và 1 tiết.
    units = [unit(f"u{i}", f"C{i}", f"T{i}") for i in range(4)]
    groups = _groups(make_problem(units))
    assert any(g.startswith("room_no_overlap:") for g in groups)


def test_unit_without_valid_room_is_reported():
    # Môn cần phòng MBA nhưng không có phòng MBA nào.
    groups = _groups(make_problem([unit("u1", "C1", "T1", room_type="mba")]))
    assert groups == ("each_unit_once:u1",)


def test_feasible_problem_has_no_conflict_groups():
    result = solve(make_problem([unit("u1", "C1", "T1")]))
    assert result.status == SolveStatus.OPTIMAL
    assert result.conflict_groups == ()


def test_diagnostic_model_does_not_change_normal_solve():
    problem = make_problem([unit("u1", "C1", "T1"), unit("u2", "C2", "T2")])
    result = solve(problem)
    assert result.timetable is not None
    assert not check_timetable(problem, result.timetable)


def test_use_case_translates_conflicts_to_vietnamese():
    problem = make_problem([unit("u1", "C1", "T1"), unit("u2", "C2", "T1")])
    outcome = SolveTimetable(CpSatSolver(), check_timetable).execute(problem, OPTIONS)
    assert outcome.diagnosis is not None
    assert outcome.diagnosis.source == "solver"
    assert len(outcome.diagnosis.issues) == 1
    assert "Giáo viên T1" in outcome.diagnosis.issues[0].message
    assert not outcome.ok


class _NeverCalled:
    def solve(self, problem, options):
        raise AssertionError("precheck phải chặn trước khi gọi solver")


def test_precheck_short_circuits_solver():
    issue = Issue("teacher_capacity", "Giáo viên T1 quá tải.", "Giảm tiết.")
    problem = make_problem([unit("u1", "C1", "T1")], grid=ONE_SLOT)
    outcome = SolveTimetable(_NeverCalled(), check_timetable, lambda _p: [issue]).execute(problem)
    assert outcome.result.status == SolveStatus.INFEASIBLE
    assert outcome.diagnosis is not None and outcome.diagnosis.source == "precheck"


def test_capacity_issues_clean_on_feasible_problem():
    assert capacity_issues(make_problem([unit("u1", "C1", "T1")])) == []


def test_describe_groups_merges_by_kind_and_truncates():
    owners = [f"T{i}" for i in range(MAX_OWNERS_SHOWN + 3)]
    report = describe_conflict_groups([f"teacher_no_overlap:{t}" for t in owners])
    assert len(report.issues) == 1
    assert "và 3 mục khác" in report.issues[0].message


def test_describe_unknown_group_is_generic():
    report = describe_conflict_groups(["xyz:A"])
    assert "xyz" in report.issues[0].message


def test_describe_no_groups():
    assert not describe_conflict_groups([]).has_issues


def test_handler_reports_precheck_diagnosis_in_json():
    # 12 lớp "khó" chỉ với 1 giáo viên: vượt sức chứa giáo viên nên báo ngay, không cần giải.
    data = generate_hard(seed=1, num_teachers=1)
    out = json.loads(
        make_solve_handler(build_default_solver, check_timetable)(json.dumps(data).encode())
    )
    assert out["status"] == "INFEASIBLE"
    assert out["assignments"] == []
    assert out["diagnosis"]["source"] == "precheck"
    assert out["diagnosis"]["issues"][0]["code"] == "teacher_capacity"


def test_handler_diagnosis_is_null_when_feasible():
    data = generate_hard(seed=1, num_classes=6, num_mba_classes=1, num_art_classes=1)
    out = json.loads(
        make_solve_handler(build_default_solver, check_timetable)(json.dumps(data).encode())
    )
    assert out["status"] in {"OPTIMAL", "FEASIBLE"}
    assert out["diagnosis"] is None


def test_solve_result_default_has_no_conflicts():
    assert SolveResult(status=SolveStatus.UNKNOWN).conflict_groups == ()

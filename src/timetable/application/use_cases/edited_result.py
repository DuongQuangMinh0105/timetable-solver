"""Kiểm tra, lưu và đọc kết quả đã được người dùng chỉnh sửa tay.

Đầu vào của job (đã lưu lúc gửi) cho biết bài toán; lịch người dùng sửa được kiểm tra lại bằng bộ
kiểm tra độc lập (ràng buộc cứng) và tính điểm phạt mềm. Bản đã sửa được lưu riêng, không ghi đè
kết quả gốc của solver.
"""

import json
from collections.abc import Callable
from typing import Any
from uuid import UUID

from timetable.application.ports.storage import StoragePort
from timetable.application.use_cases.get_job import JobNotFoundError
from timetable.domain.entities import Assignment, Problem, Timetable
from timetable.domain.ports.job_repository import JobRepositoryPort
from timetable.domain.services.validation_report import ValidationReport, build_report

ProblemLoader = Callable[[dict[str, Any]], Problem]
MBA_ROOM_TYPE = "mba"
DEFAULT_MBA_ROOM = "G316"


class EditedResultNotFoundError(Exception):
    """Job chưa có kết quả đã sửa."""


def edited_ref(job_id: UUID) -> str:
    return f"jobs/{job_id}/edited_result.json"


def _timetable(rows: list[dict[str, Any]]) -> Timetable:
    return Timetable(
        tuple(
            Assignment(
                unit_id=str(r["unit_id"]),
                day=int(r["day"]),
                period=int(r["start_period"]),
                room_id=str(r["room_id"]),
            )
            for r in rows
        )
    )


def _report_to_dict(report: ValidationReport) -> dict[str, Any]:
    violations = [
        {"rule_id": v.rule_id, "description": v.description, "severity": "HARD"}
        for v in report.hard
    ] + [
        {
            "rule_id": v.rule_id,
            "description": f"{v.description} (phạt {v.penalty})",
            "severity": "SOFT",
        }
        for v in report.soft
    ]
    summary = report.summary()
    return {
        "violations": violations,
        "summary": {
            "hard": summary["hard"],
            "soft": summary["soft"],
            "soft_penalty": summary["soft_penalty"],
        },
    }


def _full_rows(problem: Problem, timetable: Timetable) -> list[dict[str, Any]]:
    """Dựng lại dòng kết quả đầy đủ (môn, lớp, giáo viên, độ dài) từ id ca học."""
    units = {u.id: u for u in problem.lesson_units}
    rows: list[dict[str, Any]] = []
    for a in timetable.assignments:
        unit = units.get(a.unit_id)
        rows.append(
            {
                "unit_id": a.unit_id,
                "course_id": unit.course_id if unit else "",
                "class_id": unit.class_id if unit else "",
                "teacher_id": unit.teacher_id if unit else "",
                "day": a.day,
                "start_period": a.period,
                "duration": unit.duration if unit else 1,
                "room_id": a.room_id,
            }
        )
    return rows


class _EditedResultBase:
    def __init__(
        self, repository: JobRepositoryPort, storage: StoragePort, load_problem: ProblemLoader
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._load_problem = load_problem

    def _problem(self, job_id: UUID) -> Problem:
        job = self._repository.get_by_id(job_id)
        if job is None:
            raise JobNotFoundError(str(job_id))
        payload = json.loads(self._storage.get(job.input_ref).decode("utf-8"))
        return self._load_problem(payload)

    def _check(
        self, problem: Problem, rows: list[dict[str, Any]]
    ) -> tuple[Timetable, dict[str, Any]]:
        timetable = _timetable(rows)
        mba_room = next(
            (r.id for r in problem.rooms if r.room_type == MBA_ROOM_TYPE), DEFAULT_MBA_ROOM
        )
        report = build_report(
            problem, timetable, mba_room_id=mba_room, weights=problem.soft_weights
        )
        return timetable, _report_to_dict(report)


class ValidateEditedResult(_EditedResultBase):
    """Kiểm tra một lịch đã sửa so với bài toán của job; không lưu gì."""

    def execute(self, job_id: UUID, rows: list[dict[str, Any]]) -> dict[str, Any]:
        _timetable_obj, checked = self._check(self._problem(job_id), rows)
        return checked


class SaveEditedResult(_EditedResultBase):
    """Lưu lịch đã sửa (kể cả khi còn vi phạm, để người dùng lưu bản nháp)."""

    def execute(self, job_id: UUID, rows: list[dict[str, Any]]) -> dict[str, Any]:
        problem = self._problem(job_id)
        timetable, checked = self._check(problem, rows)
        saved = {"assignments": _full_rows(problem, timetable), **checked}
        self._storage.put(edited_ref(job_id), json.dumps(saved, ensure_ascii=False).encode("utf-8"))
        return saved


class GetEditedResult:
    def __init__(self, repository: JobRepositoryPort, storage: StoragePort) -> None:
        self._repository = repository
        self._storage = storage

    def execute(self, job_id: UUID) -> dict[str, Any]:
        if self._repository.get_by_id(job_id) is None:
            raise JobNotFoundError(str(job_id))
        ref = edited_ref(job_id)
        if not self._storage.exists(ref):
            raise EditedResultNotFoundError(str(job_id))
        saved: dict[str, Any] = json.loads(self._storage.get(ref).decode("utf-8"))
        return saved

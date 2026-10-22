from __future__ import annotations

from collections.abc import Iterable

from timetable.application.dto.diagnosis_report import DiagnosisReport
from timetable.application.ports.infeasibility_diagnoser import InfeasibilityDiagnoser
from timetable.domain.services.precheck import Issue, OfferingInfo, precheck

# Group names đã chốt với P1 (theo docs/diagnosis.md)
GROUP_MESSAGES: dict[str, tuple[str, str]] = {
    "each_unit_once": (
        "Mỗi đơn vị học (unit) phải được xếp đúng một lần, nhưng có unit bị xếp trùng hoặc thiếu.",
        "Kiểm tra lại dữ liệu đầu vào (số tiết môn học, số unit).",
    ),
    "room_no_overlap": (
        "Không đủ phòng học để tránh trùng lịch trong cùng một tiết.",
        "Thêm phòng học hoặc giảm số buổi học cần xếp.",
    ),
    "teacher_no_overlap": (
        "Một giáo viên bị trùng lịch dạy trong cùng một tiết.",
        "Giảm tải cho giáo viên hoặc thêm giáo viên mới.",
    ),
    "class_no_overlap": (
        "Một lớp bị trùng lịch học trong cùng một tiết.",
        "Kiểm tra lại phân bổ môn học cho lớp hoặc giảm số tiết.",
    ),
    "max_consecutive_periods": (
        "Quy định giới hạn số tiết liên tiếp bị vi phạm (ví dụ: lớp học quá 2 tiết liên tục).",
        "Điều chỉnh lại số tiết mỗi ngày hoặc tăng giới hạn liên tiếp.",
    ),
}

_UNKNOWN = (
    "Nhóm ràng buộc '{g}' xung đột với các ràng buộc khác.",
    "Liên hệ nhóm phát triển để kiểm tra nhóm ràng buộc này.",
)


class DiagnoseInfeasibility:
    def __init__(self, diagnoser: InfeasibilityDiagnoser) -> None:
        self._diagnoser = diagnoser

    def execute(
        self,
        offerings: Iterable[OfferingInfo],
        regular_room_count: int,
        design_room_count: int = 1,
    ) -> DiagnosisReport:
        issues = precheck(offerings, regular_room_count, design_room_count)
        if issues:
            return DiagnosisReport(issues=tuple(issues), source="precheck")

        groups = self._diagnoser.conflicting_groups()
        if not groups:
            return DiagnosisReport(issues=(), source="none")

        translated = []
        for g in groups:
            msg, hint = GROUP_MESSAGES.get(g, (_UNKNOWN[0].format(g=g), _UNKNOWN[1]))
            translated.append(Issue(code=g, message=msg, suggestion=hint))
        return DiagnosisReport(issues=tuple(translated), source="solver")

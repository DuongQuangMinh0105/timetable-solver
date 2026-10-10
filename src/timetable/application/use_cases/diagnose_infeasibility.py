from __future__ import annotations

from collections.abc import Iterable

from timetable.application.dto.diagnosis_report import DiagnosisReport
from timetable.application.ports.infeasibility_diagnoser import InfeasibilityDiagnoser
from timetable.domain.services.precheck import Issue, OfferingInfo, precheck

# Group names must be agreed with P1 (they name the enforcement literals).
GROUP_MESSAGES: dict[str, tuple[str, str]] = {
    "room_clash": (
        "There are not enough rooms to avoid double-booking in the same period.",
        "Add rooms or reduce the number of sessions.",
    ),
    "teacher_clash": (
        "A teacher is double-booked in the same period.",
        "Reduce teacher load or add teachers.",
    ),
    "teacher_availability": (
        "Teacher availability is too restrictive.",
        "Open more available time slots for teachers.",
    ),
    "mba_room": (
        "MBA offerings must use G316, but G316 does not have enough periods.",
        "Reduce MBA sessions or open more time slots.",
    ),
    "design_room": (
        "Design offerings must use G313, but G313 does not have enough periods.",
        "Reduce Design sessions or open more time slots.",
    ),
    "no_period_7_8": (
        "The rule forbidding periods 7 and 8 conflicts with other constraints.",
        "Compare the number of sessions to schedule with the usable periods.",
    ),
    "consecutive_limit": (
        "The rule limiting consecutive periods conflicts with other constraints.",
        "Review the number of sessions per day for each offering.",
    ),
}

_UNKNOWN = (
    "Constraint group '{g}' conflicts with other constraints.",
    "Contact the development team to investigate this group.",
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

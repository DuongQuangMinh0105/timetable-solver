from __future__ import annotations

from dataclasses import dataclass

from timetable.domain.services.precheck import Issue


@dataclass(frozen=True)
class DiagnosisReport:
    issues: tuple[Issue, ...]
    source: str  # "precheck" | "solver" | "none"

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)

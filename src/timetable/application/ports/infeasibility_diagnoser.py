from __future__ import annotations

from typing import Protocol


class InfeasibilityDiagnoser(Protocol):
    def conflicting_groups(self) -> list[str]:
        """Names of hard-constraint groups that conflict with each other."""
        ...

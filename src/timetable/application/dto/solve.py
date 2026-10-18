from dataclasses import dataclass, field
from enum import StrEnum

from timetable.domain.entities import Timetable


class SolveStatus(StrEnum):
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"
    MODEL_INVALID = "MODEL_INVALID"


@dataclass(frozen=True, slots=True)
class SolveOptions:
    time_limit_s: float = 60.0
    num_workers: int = 8
    random_seed: int = 0


@dataclass(frozen=True, slots=True)
class SolveResult:
    status: SolveStatus
    timetable: Timetable | None = None
    objective: float | None = None
    optimal: bool = False
    objective_bound: float | None = None
    # Giá trị từng số hạng của hàm mục tiêu (room, sat, g316...), nếu có.
    cost_terms: dict[str, int] = field(default_factory=dict)
    # SolveStats sẽ được P2 bổ sung sau.

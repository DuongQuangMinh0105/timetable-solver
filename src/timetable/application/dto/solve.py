from dataclasses import dataclass
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
    num_workers: int = 8  # đặt bằng số vCPU của job giải
    random_seed: int = 0


@dataclass(frozen=True, slots=True)
class SolveResult:
    status: SolveStatus
    timetable: Timetable | None = None
    objective: float | None = None
    # SolveStats (thời gian, số biến, ...) sẽ được P2 bổ sung sau.

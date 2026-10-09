from typing import Protocol


class SolverPort(Protocol):
    """Chạy bộ giải xếp lịch. Hiện thực: OR-Tools CP-SAT."""
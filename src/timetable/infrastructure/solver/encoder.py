from dataclasses import dataclass, field
from typing import Protocol

from ortools.sat.python import cp_model

from timetable.domain.entities import Problem

# Khóa biến quyết định x[u, d, p, r] = (unit_id, day, period, room_id)
VarKey = tuple[str, int, int, str]


@dataclass(slots=True)
class ModelContext:
    """Dữ liệu dùng chung giữa các encoder khi dựng mô hình CP-SAT."""

    problem: Problem
    model: cp_model.CpModel
    # x[(u, d, p, r)] = 1 nếu đơn vị học u được xếp vào ngày d, tiết p, phòng r
    x: dict[VarKey, cp_model.IntVar] = field(default_factory=dict)
    # Các số hạng phạt của ràng buộc mềm: (trọng số, biến). Hàm mục tiêu = tổng w * biến.
    penalties: list[tuple[int, cp_model.IntVar]] = field(default_factory=list)


class ConstraintEncoder(Protocol):
    """Mỗi ràng buộc (cứng hoặc mềm) là một encoder thêm điều kiện vào mô hình."""

    name: str

    def encode(self, ctx: ModelContext) -> None: ...

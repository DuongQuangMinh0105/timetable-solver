from dataclasses import dataclass, field
from typing import Protocol

from ortools.sat.python import cp_model

from timetable.domain.entities import Problem

# Khóa biến bắt đầu s[u, d, p, r] = (unit_id, day, start_period, room_id)
VarKey = tuple[str, int, int, str]


@dataclass(slots=True)
class ModelContext:
    """Dữ liệu dùng chung giữa các encoder khi dựng mô hình CP-SAT."""

    problem: Problem
    model: cp_model.CpModel
    # s[(u, d, p, r)] = 1 nếu đơn vị học u BẮT ĐẦU ở ngày d, tiết p, phòng r (chiếm `duration` tiết)
    s: dict[VarKey, cp_model.IntVar] = field(default_factory=dict)
    # Các số hạng phạt của ràng buộc mềm: (trọng số, biến). Hàm mục tiêu = tổng w * biến.
    penalties: list[tuple[int, cp_model.IntVar]] = field(default_factory=list)
    # Từng số hạng của hàm mục tiêu (room, sat, g316...), để giải thích điểm phạt của một lịch.
    cost_terms: dict[str, object] = field(default_factory=dict)


class ConstraintEncoder(Protocol):
    """Mỗi ràng buộc (cứng hoặc mềm) là một encoder thêm điều kiện vào mô hình."""

    name: str

    def encode(self, ctx: ModelContext) -> None: ...


class ObjectiveApplier(Protocol):
    """Gắn hàm mục tiêu vào mô hình sau khi mọi encoder đã chạy (ObjectiveBuilder của P2)."""

    def apply(self, ctx: ModelContext) -> None: ...

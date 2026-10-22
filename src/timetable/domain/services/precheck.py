"""Kiểm tra trước (precheck) các điều kiện cơ bản trước khi gọi solver."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

# Sức chứa tối đa của một phòng học (số sinh viên)
ROOM_MAX_CAPACITY = 30
# Số tiết tối đa một phòng có thể dạy trong tuần (6 ngày x 6 tiết)
ROOM_WEEKLY_CAPACITY = 36


@dataclass(frozen=True)
class OfferingInfo:
    """Thông tin tóm tắt của một lớp/môn cần xếp lịch."""

    id: str
    kind: str  # "regular", "mba", "design"
    size: int
    periods_per_week: int
    teacher_id: str


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    suggestion: str = ""


def precheck(
    offerings: Iterable[OfferingInfo],
    regular_room_count: int,
    design_room_count: int = 1,
) -> list[Issue]:
    issues: list[Issue] = []
    offerings = list(offerings)

    # 1. Kiểm tra sức chứa từng phòng (số sinh viên)
    for o in offerings:
        if o.size > ROOM_MAX_CAPACITY:
            issues.append(
                Issue(
                    code="room_capacity",
                    message=f"Lớp {o.id} có {o.size} sinh viên, vượt sức chứa tối đa "
                    f"của phòng ({ROOM_MAX_CAPACITY}).",
                    suggestion="Giảm sĩ số hoặc tăng sức chứa phòng.",
                )
            )

    # 2. Kiểm tra TỔNG sức chứa của tất cả phòng thường (số sinh viên)
    regular_offerings = [o for o in offerings if o.kind == "regular"]
    if regular_offerings:
        total_students = sum(o.size for o in regular_offerings)
        total_capacity = regular_room_count * ROOM_MAX_CAPACITY
        if total_students > total_capacity:
            issues.append(
                Issue(
                    code="regular_room_capacity_total",
                    message=f"Tổng số sinh viên lớp thường ({total_students}) vượt quá "
                    f"sức chứa của {regular_room_count} phòng ({total_capacity}).",
                    suggestion="Thêm phòng học hoặc giảm sĩ số.",
                )
            )

    # 3. Kiểm tra tổng số tiết lớp thường so với số phòng
    if regular_offerings:
        total_regular_periods = sum(o.periods_per_week for o in regular_offerings)
        regular_capacity = regular_room_count * ROOM_WEEKLY_CAPACITY
        if total_regular_periods > regular_capacity:
            issues.append(
                Issue(
                    code="regular_room_overload",
                    message=f"Tổng số tiết lớp thường ({total_regular_periods}) vượt quá "
                    f"sức chứa của {regular_room_count} phòng ({regular_capacity} tiết).",
                    suggestion="Thêm phòng học thường hoặc giảm số tiết.",
                )
            )

    # 4. Kiểm tra tổng số tiết lớp Design so với số phòng G313
    design_offerings = [o for o in offerings if o.kind == "design"]
    if design_offerings:
        total_design_periods = sum(o.periods_per_week for o in design_offerings)
        design_capacity = design_room_count * ROOM_WEEKLY_CAPACITY
        if total_design_periods > design_capacity:
            issues.append(
                Issue(
                    code="design_room_overload",
                    message=f"Tổng số tiết Design ({total_design_periods}) vượt quá "
                    f"sức chứa của {design_room_count} phòng G313 ({design_capacity} tiết).",
                    suggestion="Giảm số lớp Design hoặc thêm phòng G313.",
                )
            )

    # 5. Kiểm tra tổng số tiết lớp MBA so với số phòng G316 (giả định 1 phòng)
    mba_offerings = [o for o in offerings if o.kind == "mba"]
    if mba_offerings:
        total_mba_periods = sum(o.periods_per_week for o in mba_offerings)
        mba_capacity = ROOM_WEEKLY_CAPACITY
        if total_mba_periods > mba_capacity:
            issues.append(
                Issue(
                    code="mba_room_overload",
                    message=f"Tổng số tiết MBA ({total_mba_periods}) vượt quá "
                    f"sức chứa của phòng G316 ({mba_capacity} tiết).",
                    suggestion="Giảm số lớp MBA hoặc mở thêm phòng G316.",
                )
            )

    return issues

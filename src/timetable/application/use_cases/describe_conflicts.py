"""Dịch tên nhóm ràng buộc xung đột (từ lõi vô nghiệm của CP-SAT) thành thông báo tiếng Việt.

Tên nhóm có dạng "loại:chủ thể" (xem `docs/diagnosis.md`), ví dụ "teacher_no_overlap:T3".
"""

from collections import defaultdict
from collections.abc import Iterable

from timetable.application.dto.diagnosis_report import DiagnosisReport
from timetable.domain.services.precheck import Issue

MAX_OWNERS_SHOWN = 5

# loại nhóm -> (thông báo có {owners}, gợi ý sửa)
KIND_MESSAGES: dict[str, tuple[str, str]] = {
    "each_unit_once": (
        "Không xếp được các ca học: {owners} (không còn ô ngày, tiết, phòng nào hợp lệ).",
        "Kiểm tra loại phòng, sức chứa phòng và các tiết được phép của những ca học này.",
    ),
    "room_no_overlap": (
        "Phòng {owners} không đủ tiết để xếp hết các ca học cần dùng, nên bị trùng giờ.",
        "Thêm phòng cùng loại hoặc giảm số tiết dùng các phòng này.",
    ),
    "teacher_no_overlap": (
        "Giáo viên {owners} bị dạy trùng giờ: số tiết được giao vượt số tiết có thể xếp.",
        "Giảm số tiết của giáo viên này hoặc phân công thêm giáo viên.",
    ),
    "class_no_overlap": (
        "Lớp {owners} bị học trùng giờ: số tiết của lớp vượt số tiết có thể xếp.",
        "Giảm số tiết của lớp hoặc mở thêm ngày, tiết học.",
    ),
    "fixed_assignments": (
        "Không giữ được các ca đã khóa: {owners} (ô khóa không hợp lệ hoặc trùng với ca khác).",
        "Mở khóa các ca này hoặc đổi sang ngày, tiết, phòng khác phù hợp.",
    ),
    "max_consecutive_periods": (
        "Lớp {owners} không xếp vừa vì quy tắc giới hạn số tiết học liên tiếp.",
        "Giảm số tiết của lớp trong tuần hoặc nới giới hạn tiết liên tiếp.",
    ),
}

_UNKNOWN = (
    "Nhóm ràng buộc '{kind}' ({owners}) mâu thuẫn với các ràng buộc khác.",
    "Liên hệ nhóm phát triển để kiểm tra nhóm này.",
)


def split_group(group: str) -> tuple[str, str]:
    kind, _, owner = group.partition(":")
    return kind, owner


def describe_conflict_groups(groups: Iterable[str]) -> DiagnosisReport:
    """Gộp các nhóm xung đột theo loại và dịch sang tiếng Việt."""
    owners_by_kind: dict[str, list[str]] = defaultdict(list)
    for group in groups:
        kind, owner = split_group(group)
        owners_by_kind[kind].append(owner or "(tất cả)")
    if len(owners_by_kind) > 1:
        # "Mỗi ca học được xếp đúng một lần" luôn nằm trong lõi khi có xung đột tài nguyên, nên
        # chỉ báo riêng khi không còn nhóm nào khác (ca học không có ô hợp lệ).
        owners_by_kind.pop("each_unit_once", None)
    issues = []
    for kind, owners in sorted(owners_by_kind.items()):
        template, suggestion = KIND_MESSAGES.get(kind, _UNKNOWN)
        shown = ", ".join(sorted(owners)[:MAX_OWNERS_SHOWN])
        if len(owners) > MAX_OWNERS_SHOWN:
            shown += f" và {len(owners) - MAX_OWNERS_SHOWN} mục khác"
        issues.append(
            Issue(
                code=kind, message=template.format(owners=shown, kind=kind), suggestion=suggestion
            )
        )
    return DiagnosisReport(issues=tuple(issues), source="solver" if issues else "none")

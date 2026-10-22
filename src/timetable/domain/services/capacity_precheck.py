"""Kiểm tra nhanh trước khi giải: các điều kiện cần về sức chứa, không cần solver."""

from timetable.domain.entities import Problem
from timetable.domain.services.block_capacity import class_capacity_issues
from timetable.domain.services.precheck import Issue
from timetable.domain.services.resource_capacity import resource_capacity_issues


def capacity_issues(problem: Problem) -> list[Issue]:
    """Gộp kiểm tra sức chứa giáo viên, phòng và lớp. Có lỗi thì chắc chắn vô nghiệm."""
    return [*resource_capacity_issues(problem), *class_capacity_issues(problem)]

"""Sức chứa theo block của một lớp: kiểm tra nhanh một lớp có thể có nghiệm hay không.

Điều kiện chỉ xét riêng từng lớp (bỏ qua giáo viên, phòng và các lớp khác), nên là điều kiện
**cần**: vi phạm thì chắc chắn vô nghiệm; thỏa thì chưa bảo đảm có nghiệm toàn cục. Với một lớp
có giáo viên và phòng không bị tranh chấp, điều kiện này cũng là điều kiện đủ.
"""

from timetable.domain.entities import Problem
from timetable.domain.services.precheck import Issue

# (số block 2 tiết, số block 1 tiết) mà một lớp có thể học trong một ngày.
DayPattern = tuple[int, int]


def day_patterns(problem: Problem) -> frozenset[DayPattern]:
    """Mọi cặp (a, b) xếp được trong một ngày: a block 2 tiết và b block 1 tiết.

    Tôn trọng tiết được phép, `block_starts` và `max_consecutive_periods` (đếm theo tiết bị chiếm).
    """
    allowed = tuple(sorted(problem.grid.allowed_periods))
    allowed_set = set(allowed)
    starts2 = [
        p
        for p in allowed
        if p + 1 in allowed_set and (problem.block_starts is None or p in problem.block_starts)
    ]
    max_run = problem.max_consecutive_periods
    found: set[DayPattern] = set()

    def run_ok(occupied: frozenset[int]) -> bool:
        run = 0
        for p in range(max(allowed) + 2):
            run = run + 1 if p in occupied else 0
            if run > max_run:
                return False
        return True

    def place(index: int, occupied: frozenset[int], a: int, b: int) -> None:
        if index == len(allowed):
            found.add((a, b))
            return
        p = allowed[index]
        place(index + 1, occupied, a, b)  # tiết p bỏ trống
        if p not in occupied:
            one = occupied | {p}
            if run_ok(one):
                place(index + 1, one, a, b + 1)
        if p in starts2 and p not in occupied and p + 1 not in occupied:
            two = occupied | {p, p + 1}
            if run_ok(two):
                place(index + 1, two, a + 1, b)

    place(0, frozenset(), 0, 0)
    return frozenset(found)


def class_fits(problem: Problem, twos: int, ones: int) -> bool:
    """Một lớp cần `twos` block 2 tiết và `ones` block 1 tiết có xếp vừa số ngày hay không."""
    patterns = day_patterns(problem)
    reachable = {(0, 0)}  # (số block 2 đã đặt, số block 1 đã đặt), cắt ở nhu cầu
    for _ in range(problem.grid.days):
        reachable |= {
            (min(twos, a + pa), min(ones, b + pb)) for (a, b) in reachable for (pa, pb) in patterns
        }
    return (twos, ones) in reachable


def class_capacity_issues(problem: Problem) -> list[Issue]:
    """Báo các lớp có số block 2 tiết và 1 tiết không thể xếp vừa trong tuần."""
    needs: dict[str, list[int]] = {}
    for u in problem.lesson_units:
        counts = needs.setdefault(u.class_id, [0, 0])
        counts[0 if u.duration >= 2 else 1] += 1
    issues: list[Issue] = []
    for class_id, (twos, ones) in sorted(needs.items()):
        if not class_fits(problem, twos, ones):
            issues.append(
                Issue(
                    "class_capacity",
                    f"Lớp {class_id} cần {twos} block 2 tiết và {ones} block 1 tiết mỗi tuần, "
                    f"nhưng quy tắc tối đa {problem.max_consecutive_periods} tiết liên tiếp "
                    f"trong {problem.grid.days} ngày không cho xếp vừa.",
                    "Giảm số tiết của lớp, hoặc mở thêm tiết hoặc ngày học.",
                )
            )
    return issues

from timetable.domain.entities import Problem, Room


def allowed_rooms_by_unit(problem: Problem) -> dict[str, tuple[Room, ...]]:
    """Phòng mà mỗi đơn vị học được phép dùng, theo loại phòng yêu cầu và sức chứa.

    - Lớp MBA (yêu cầu `mba`) chỉ vào phòng MBA (G316).
    - Môn vẽ (yêu cầu `art`) chỉ vào phòng vẽ (G313).
    - Môn thường (yêu cầu `standard`) vào phòng thường và cả phòng MBA nếu phòng đó hỗ trợ.
    - Phòng phải đủ sức chứa cho lớp.
    """
    size_by_class = {c.id: c.size for c in problem.class_groups}
    result: dict[str, tuple[Room, ...]] = {}
    for unit in problem.lesson_units:
        if unit.class_id not in size_by_class:
            raise ValueError(f"Đơn vị học {unit.id} tham chiếu lớp không tồn tại: {unit.class_id}")
        size = size_by_class[unit.class_id]
        result[unit.id] = tuple(
            room
            for room in problem.rooms
            if room.can_host(unit.required_room_type) and room.capacity >= size
        )
    return result

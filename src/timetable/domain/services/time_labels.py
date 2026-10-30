"""Tên ngày và tiết để hiển thị cho người dùng (chỉ số trong mô hình bắt đầu từ 0)."""

DAY_NAMES = ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật")


def day_name(day: int) -> str:
    """Ngày 0 là Thứ Hai ... ngày 5 là Thứ Bảy."""
    return DAY_NAMES[day] if 0 <= day < len(DAY_NAMES) else f"ngày {day + 1}"


def period_name(period: int) -> str:
    """Tiết 0 trong mô hình hiển thị là "tiết 1"."""
    return f"tiết {period + 1}"


def slot_name(day: int, period: int) -> str:
    return f"{day_name(day)}, {period_name(period)}"

"""Định dạng chẩn đoán vô nghiệm để hiển thị (không phụ thuộc streamlit nên dễ kiểm thử)."""

from typing import Any

SOURCE_TITLES = {
    "precheck": "Dữ liệu đầu vào không thể xếp được (phát hiện trước khi giải)",
    "solver": "Các nhóm ràng buộc xung đột (do bộ giải xác định)",
}
FALLBACK_TITLE = "Không thể xếp lịch với dữ liệu này"
TIMEOUT_TITLE = "Chưa tìm ra lịch trong thời gian cho phép"


def diagnosis_title(result: dict[str, Any]) -> str:
    diagnosis = result.get("diagnosis") or {}
    if diagnosis.get("source", "") in SOURCE_TITLES:
        return SOURCE_TITLES[diagnosis["source"]]
    # UNKNOWN là hết giờ mà chưa có kết luận, khác với INFEASIBLE (đã chứng minh vô nghiệm).
    return TIMEOUT_TITLE if result.get("status") == "UNKNOWN" else FALLBACK_TITLE


def diagnosis_lines(result: dict[str, Any]) -> list[str]:
    """Mỗi lý do thành một dòng markdown: thông báo kèm gợi ý sửa. Rỗng nếu không có chẩn đoán."""
    diagnosis = result.get("diagnosis") or {}
    return [
        f"**{issue['message']}**  \n_Gợi ý:_ {issue['suggestion']}"
        for issue in diagnosis.get("issues", [])
    ]


def needs_diagnosis(result: dict[str, Any]) -> bool:
    return result.get("status") in ("INFEASIBLE", "UNKNOWN") and not result.get("assignments")

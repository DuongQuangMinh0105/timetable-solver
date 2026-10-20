import io
import tempfile
import time
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import streamlit as st

from timetable.application.ports.excel_importer import ExcelImportError
from timetable.infrastructure.excel.importer import OpenpyxlExcelImporter
from timetable.interfaces.ui.client import ApiError, SolverApiClient

st.set_page_config(
    page_title="Hệ thống Xếp Thời khoá biểu",
    page_icon="📅",
    layout="wide",
)


def export_schedule_to_excel(assignments: list[dict[str, Any]]) -> bytes:
    """Xuất danh sách phân công lịch học ra file Excel."""
    output = io.BytesIO()
    df = pd.DataFrame(assignments)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="ThoiKhoaBieu")
    return output.getvalue()


def render_dashboard(result_data: dict[str, Any]) -> None:
    """Hiển thị các Tab giao diện sau khi giải thành công."""
    status = result_data.get("status", "UNKNOWN")
    objective = result_data.get("objective", 0)
    assignments = result_data.get("assignments", [])
    violations = result_data.get("violations", [])

    # Chia các Tab chức năng
    tab_summary, tab_class, tab_teacher, tab_room = st.tabs(
        [
            "📊 Tổng quan & Vi phạm",
            "🏫 Lịch theo Lớp",
            "👨‍🏫 Lịch theo Giáo viên",
            "🚪 Lịch theo Phòng",
        ]
    )

    # --- TAB 1: TỔNG QUAN & VI PHẠM ---
    with tab_summary:
        st.subheader("Trạng thái Giải & Phân tích Vi phạm")

        hard_violations = [v for v in violations if v.get("severity") == "HARD"]
        soft_violations = [v for v in violations if v.get("severity") == "SOFT"]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Trạng thái Solver", status)
        col2.metric("Objective Cost", objective)
        col3.metric("Vi phạm HARD", len(hard_violations))
        col4.metric("Vi phạm SOFT", len(soft_violations))

        st.markdown("---")
        st.write("### Chi tiết danh sách vi phạm")
        if violations:
            df_violations = pd.DataFrame(violations)
            st.dataframe(df_violations, use_container_width=True)
        else:
            st.success("🎉 Không tìm thấy vi phạm nào! Lịch học hoàn hảo.")

    if not assignments:
        st.warning("Chưa có dữ liệu phân công để hiển thị lịch.")
        return

    df_assign = pd.DataFrame(assignments)

    # --- TAB 2: LỊCH THEO LỚP ---
    with tab_class:
        st.subheader("Thời khóa biểu chi tiết theo Lớp học")
        if "class_id" in df_assign.columns:
            class_list = sorted(df_assign["class_id"].dropna().unique())
            selected_class = st.selectbox("Chọn lớp học:", class_list, key="select_class")
            df_class = df_assign[df_assign["class_id"] == selected_class]
            st.dataframe(df_class, use_container_width=True)
        else:
            st.dataframe(df_assign, use_container_width=True)

    # --- TAB 3: LỊCH THEO GIÁO VIÊN ---
    with tab_teacher:
        st.subheader("Thời khóa biểu chi tiết theo Giáo viên")
        if "teacher_id" in df_assign.columns:
            teacher_list = sorted(df_assign["teacher_id"].dropna().unique())
            selected_teacher = st.selectbox("Chọn giáo viên:", teacher_list, key="select_teacher")
            df_teacher = df_assign[df_assign["teacher_id"] == selected_teacher]
            st.dataframe(df_teacher, use_container_width=True)
        else:
            st.dataframe(df_assign, use_container_width=True)

    # --- TAB 4: LỊCH THEO PHÒNG ---
    with tab_room:
        st.subheader("Lịch sử dụng Phòng học")
        if "room_id" in df_assign.columns:
            room_list = sorted(df_assign["room_id"].dropna().unique())
            selected_room = st.selectbox("Chọn phòng học:", room_list, key="select_room")
            df_room = df_assign[df_assign["room_id"] == selected_room]
            st.dataframe(df_room, use_container_width=True)
        else:
            st.dataframe(df_assign, use_container_width=True)

    # --- NÚT XUẤT EXCEL Ở SIDEBAR ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Xuất dữ liệu")
    excel_bytes = export_schedule_to_excel(assignments)
    st.sidebar.download_button(
        label="📥 Tải lịch học Excel (.xlsx)",
        data=excel_bytes,
        file_name="thoi_khoa_bieu_ket_qua.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def main() -> None:
    st.title("📅 Hệ thống Xếp Thời khóa biểu")
    client = SolverApiClient()

    st.sidebar.header("📂 Dữ liệu đầu vào")
    uploaded = st.sidebar.file_uploader(
        "Tải file Excel (sheet Phòng, Giáo viên, Lớp, Môn)", type=["xlsx"]
    )

    if st.sidebar.button("🚀 Bắt đầu Giải", disabled=uploaded is None) and uploaded is not None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.xlsx"
            path.write_bytes(uploaded.getvalue())
            try:
                payload = OpenpyxlExcelImporter().load_data(path)
            except ExcelImportError as exc:
                st.error(f"Lỗi đọc file Excel đầu vào: {exc}")
                return
        try:
            job_id = client.submit(payload)
            st.session_state["job_id"] = job_id
            st.session_state.pop("result_data", None)
        except ApiError as exc:
            st.error(f"Lỗi gửi yêu cầu giải: {exc}")
            return

    current_job = st.session_state.get("job_id")
    if current_job:
        st.info(f"Mã tiến trình (Job ID): `{current_job}`")

        # Kiểm tra nếu chưa có kết quả trong session state thì poll status từ backend
        if "result_data" not in st.session_state:
            placeholder = st.empty()
            try:
                for _ in range(120):
                    info = client.job_status(current_job)
                    status = info.get("status", "UNKNOWN")
                    placeholder.info(f"Trạng thái tiến trình: **{status}**")

                    if client.is_final(status):
                        st.session_state["result_data"] = info.get("result", info)
                        placeholder.empty()
                        break
                    time.sleep(2)
            except ApiError as exc:
                st.error(f"Lỗi cập nhật trạng thái job: {exc}")
                return

    # Hiển thị Dashboard giao diện nếu đã có kết quả
    result_data = st.session_state.get("result_data")
    if result_data:
        render_dashboard(result_data)


if __name__ == "__main__":
    main()

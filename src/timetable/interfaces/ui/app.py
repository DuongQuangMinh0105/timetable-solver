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
from timetable.interfaces.ui.diagnosis_view import (
    diagnosis_lines,
    diagnosis_title,
    needs_diagnosis,
)
from timetable.interfaces.ui.result_edit import (
    LOCKED,
    READ_ONLY,
    fixed_assignments,
    to_api_rows,
    to_edit_rows,
)
from timetable.interfaces.ui.tables import (
    CLASS_COLUMNS,
    COURSE_COLUMNS,
    ROOM_COLUMNS,
    TEACHER_COLUMNS,
    payload_to_tables,
    tables_to_payload,
)

DEFAULT_TIME_LIMIT_S = 120

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


def render_dashboard(
    result_data: dict[str, Any],
    client: SolverApiClient | None = None,
    job_id: str | None = None,
    base_payload: dict[str, Any] | None = None,
) -> None:
    """Hiển thị các Tab giao diện sau khi giải thành công (kèm tab sửa kết quả nếu có API)."""
    status = result_data.get("status", "UNKNOWN")
    objective = result_data.get("objective", 0)
    assignments = result_data.get("assignments", [])
    violations = result_data.get("violations", [])

    if status == "FAILED":
        st.error(
            "Job thất bại (lịch sai ràng buộc cứng hoặc lỗi hệ thống). "
            "Xem log của worker hoặc thử lại với dữ liệu khác."
        )

    if needs_diagnosis(result_data):
        lines = diagnosis_lines(result_data)
        timed_out = status == "UNKNOWN" and not lines
        title = f"**{diagnosis_title(result_data)}** (trạng thái {status})"
        if timed_out:
            st.warning(title)
        else:
            st.error(title)
        for line in lines:
            st.markdown(f"- {line}")
        if timed_out:
            st.markdown(
                "Bộ giải chưa kịp tìm ra lịch trong thời gian giới hạn. "
                "**Điều này không có nghĩa dữ liệu vô nghiệm.** Thử lần lượt:\n"
                "- Tăng **Thời gian giải tối đa** ở tab 1 (ví dụ 300 giây).\n"
                "- Giảm số lớp hoặc số môn, hoặc dùng file mẫu nhỏ hơn.\n"
                "- Chạy API trên máy nhiều CPU hơn (Render miễn phí chỉ có 0,1 CPU nên giải chậm)."
            )
        elif not lines:
            st.info("Chưa xác định được nhóm ràng buộc gây xung đột.")

    # Chia các Tab chức năng
    labels = [
        "📊 Tổng quan & Vi phạm",
        "🏫 Lịch theo Lớp",
        "👨‍🏫 Lịch theo Giáo viên",
        "🚪 Lịch theo Phòng",
    ]
    can_edit = client is not None and job_id is not None and bool(assignments)
    if can_edit:
        labels.append("✏️ Sửa kết quả")
    tabs = st.tabs(labels, key="dashboard_tabs")
    tab_summary, tab_class, tab_teacher, tab_room = tabs[:4]

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
            st.dataframe(df_violations, width="stretch")
        elif assignments:
            st.success("🎉 Không tìm thấy vi phạm nào! Lịch học hoàn hảo.")
        else:
            st.info("Không có lịch để kiểm tra vi phạm (xem chẩn đoán phía trên).")

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
            st.dataframe(df_class, width="stretch")
        else:
            st.dataframe(df_assign, width="stretch")

    # --- TAB 3: LỊCH THEO GIÁO VIÊN ---
    with tab_teacher:
        st.subheader("Thời khóa biểu chi tiết theo Giáo viên")
        if "teacher_id" in df_assign.columns:
            teacher_list = sorted(df_assign["teacher_id"].dropna().unique())
            selected_teacher = st.selectbox("Chọn giáo viên:", teacher_list, key="select_teacher")
            df_teacher = df_assign[df_assign["teacher_id"] == selected_teacher]
            st.dataframe(df_teacher, width="stretch")
        else:
            st.dataframe(df_assign, width="stretch")

    # --- TAB 4: LỊCH THEO PHÒNG ---
    with tab_room:
        st.subheader("Lịch sử dụng Phòng học")
        if "room_id" in df_assign.columns:
            room_list = sorted(df_assign["room_id"].dropna().unique())
            selected_room = st.selectbox("Chọn phòng học:", room_list, key="select_room")
            df_room = df_assign[df_assign["room_id"] == selected_room]
            st.dataframe(df_room, width="stretch")
        else:
            st.dataframe(df_assign, width="stretch")

    # --- TAB 5: SỬA KẾT QUẢ ---
    if can_edit and client is not None and job_id is not None:
        with tabs[4]:
            render_editor(client, job_id, assignments, base_payload)

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


def render_input_editor(client: SolverApiClient) -> None:
    """Cho sửa dữ liệu đầu vào (phòng, giáo viên, lớp, môn, lưới) rồi bấm lưu để giải."""
    draft = st.session_state.get("draft")
    if draft is None:
        st.info("Tải file Excel ở thanh bên rồi bấm **Đọc file** để xem và sửa dữ liệu.")
        return
    version = st.session_state.get("draft_version", 0)
    st.caption("Sửa trực tiếp trong bảng (thêm dòng ở cuối, chọn dòng rồi bấm Delete để xóa).")
    t_room, t_teacher, t_class, t_course, t_grid = st.tabs(
        ["🚪 Phòng", "👨‍🏫 Giáo viên", "🏫 Lớp", "📚 Môn", "🗓️ Lưới giờ"]
    )
    edited: dict[str, Any] = {}
    columns = {
        "rooms": ROOM_COLUMNS,
        "teachers": TEACHER_COLUMNS,
        "classes": CLASS_COLUMNS,
        "courses": COURSE_COLUMNS,
    }
    for tab, key in (
        (t_room, "rooms"),
        (t_teacher, "teachers"),
        (t_class, "classes"),
        (t_course, "courses"),
    ):
        with tab:
            frame = st.data_editor(
                pd.DataFrame(draft[key], columns=list(columns[key])),
                num_rows="dynamic",
                width="stretch",
                key=f"in_{key}_{version}",
            )
            edited[key] = frame.to_dict("records")
    with t_grid:
        grid = draft["grid"]
        days = st.number_input(
            "Số ngày học trong tuần", 1, 7, int(grid["days"]), key=f"g_d_{version}"
        )
        periods = st.number_input(
            "Số tiết mỗi ngày", 1, 12, int(grid["periods"]), key=f"g_p_{version}"
        )
        allowed = st.text_input(
            "Các tiết được xếp (đánh số từ 1, cách nhau dấu phẩy)",
            str(grid["allowed_periods"]),
            key=f"g_a_{version}",
        )
        edited["grid"] = {"days": days, "periods": periods, "allowed_periods": allowed}

    time_limit = st.number_input(
        "⏱️ Thời gian giải tối đa (giây)",
        min_value=10,
        max_value=900,
        value=int(st.session_state["base_payload"].get("time_limit_s") or DEFAULT_TIME_LIMIT_S),
        step=10,
        help="Bộ giải dừng khi hết thời gian và trả nghiệm tốt nhất đã có. "
        "Dữ liệu lớn hoặc máy yếu cần đặt cao hơn.",
        key=f"tl_{version}",
    )
    if st.button("💾 Lưu và giải", type="primary", key=f"solve_{version}"):
        payload, errors = tables_to_payload(edited, st.session_state["base_payload"])
        if errors:
            st.error("Dữ liệu chưa hợp lệ, hãy sửa rồi lưu lại:")
            for error in errors:
                st.markdown(f"- {error}")
            return
        assert payload is not None
        payload["time_limit_s"] = float(time_limit)
        submit_job(client, payload)


def submit_job(client: SolverApiClient, payload: dict[str, Any]) -> None:
    try:
        job_id = client.submit(payload)
    except ApiError as exc:
        st.error(f"Lỗi gửi yêu cầu giải: {exc}")
        return
    st.session_state["job_id"] = job_id
    st.session_state["solved_payload"] = payload
    st.session_state.pop("result_data", None)
    st.session_state.pop("edit_check", None)
    st.rerun()


def render_editor(
    client: SolverApiClient,
    job_id: str,
    assignments: list[dict[str, Any]],
    base_payload: dict[str, Any] | None,
) -> None:
    """Sửa lịch đã giải: đổi ngày, tiết, phòng; kiểm tra, lưu, tải Excel hoặc giải lại."""
    rooms = (
        [r["id"] for r in base_payload["rooms"]]
        if base_payload
        else sorted({a["room_id"] for a in assignments})
    )
    st.caption(
        "Sửa cột day, start_period (số từ 0) và room_id. Đánh dấu **locked** để giữ nguyên ca "
        "đó khi giải lại; ca đã sửa cũng tự được giữ."
    )
    frame = st.data_editor(
        pd.DataFrame(to_edit_rows(assignments)),
        key=f"edit_{job_id}",
        width="stretch",
        disabled=list(READ_ONLY),
        column_config={
            "room_id": st.column_config.SelectboxColumn("room_id", options=rooms, required=True),
            LOCKED: st.column_config.CheckboxColumn("locked"),
        },
    )
    rows: list[dict[str, Any]] = frame.to_dict("records")
    api_rows, input_errors = to_api_rows(rows)
    for error in input_errors:
        st.warning(error)

    col_check, col_save, col_solve = st.columns(3)
    if col_check.button("🔍 Kiểm tra", key=f"check_{job_id}", disabled=bool(input_errors)):
        try:
            st.session_state["edit_check"] = client.validate_edited(job_id, api_rows)
        except ApiError as exc:
            st.error(f"Lỗi kiểm tra lịch: {exc}")
    if col_save.button("💾 Lưu bản sửa", key=f"save_{job_id}", disabled=bool(input_errors)):
        try:
            st.session_state["edit_check"] = client.save_edited(job_id, api_rows)
            st.success("Đã lưu bản sửa (kết quả gốc của bộ giải vẫn được giữ).")
        except ApiError as exc:
            st.error(f"Lỗi lưu bản sửa: {exc}")
    if col_solve.button(
        "🔁 Giải lại, giữ ca đã sửa/khóa",
        key=f"resolve_{job_id}",
        disabled=bool(input_errors) or base_payload is None,
    ):
        keep = fixed_assignments(rows, assignments)
        assert base_payload is not None
        submit_job(client, {**base_payload, "fixed_assignments": keep})

    check = st.session_state.get("edit_check")
    if check:
        summary = check.get("summary", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Vi phạm cứng", summary.get("hard", 0))
        c2.metric("Vi phạm mềm", summary.get("soft", 0))
        c3.metric("Điểm phạt mềm", summary.get("soft_penalty", 0))
        if check.get("violations"):
            st.dataframe(pd.DataFrame(check["violations"]), width="stretch")
        else:
            st.success("Lịch đã sửa không vi phạm ràng buộc nào.")
    st.download_button(
        "📥 Tải lịch đã sửa (.xlsx)",
        data=export_schedule_to_excel(rows),
        file_name="thoi_khoa_bieu_da_sua.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"dl_{job_id}",
    )


def main() -> None:
    st.title("📅 Hệ thống Xếp Thời khóa biểu")
    client = SolverApiClient()

    st.sidebar.header("📂 Dữ liệu đầu vào")
    uploaded = st.sidebar.file_uploader(
        "Tải file Excel (mẫu tiếng Việt hoặc tiếng Anh, xem docs/samples)", type=["xlsx"]
    )
    if st.sidebar.button("📖 Đọc file", disabled=uploaded is None) and uploaded is not None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.xlsx"
            path.write_bytes(uploaded.getvalue())
            try:
                importer = OpenpyxlExcelImporter()
                payload = importer.load_data(path)
            except ExcelImportError as exc:
                st.error(f"Lỗi đọc file Excel đầu vào: {exc}")
                return
        st.session_state["draft"] = payload_to_tables(payload)
        st.session_state["base_payload"] = payload
        st.session_state["draft_version"] = st.session_state.get("draft_version", 0) + 1
        st.session_state["import_warnings"] = list(importer.warnings)
        for key in ("job_id", "result_data", "solved_payload", "edit_check"):
            st.session_state.pop(key, None)

    for warning in st.session_state.get("import_warnings", []):
        st.warning(warning)

    tab_input, tab_result = st.tabs(
        ["1️⃣ Dữ liệu đầu vào (sửa được)", "2️⃣ Kết quả và chỉnh sửa"], key="main_tabs"
    )
    with tab_input:
        render_input_editor(client)

    with tab_result:
        current_job = st.session_state.get("job_id")
        if not current_job:
            st.info("Chưa có kết quả. Sửa dữ liệu (nếu cần) rồi bấm **Lưu và giải** ở tab 1.")
            return
        st.info(f"Mã tiến trình (Job ID): `{current_job}`")

        if "result_data" not in st.session_state:
            placeholder = st.empty()
            try:
                for _ in range(120):
                    info = client.job_status(current_job)
                    status = info.get("status", "UNKNOWN")
                    placeholder.info(f"Trạng thái tiến trình: **{status}**")
                    if client.is_final(status):
                        if status.upper() == "DONE":
                            st.session_state["result_data"] = client.job_result(current_job)
                        else:
                            st.session_state["result_data"] = {"status": "FAILED", **info}
                        placeholder.empty()
                        break
                    time.sleep(2)
            except ApiError as exc:
                st.error(f"Lỗi cập nhật trạng thái job: {exc}")
                return

        result_data = st.session_state.get("result_data")
        if result_data:
            render_dashboard(
                result_data,
                client=client,
                job_id=current_job,
                base_payload=st.session_state.get("solved_payload")
                or st.session_state.get("base_payload"),
            )


if __name__ == "__main__":
    main()

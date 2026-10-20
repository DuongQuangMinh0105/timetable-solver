import tempfile
import time
from pathlib import Path

import streamlit as st

from timetable.application.ports.excel_importer import ExcelImportError
from timetable.infrastructure.excel.importer import OpenpyxlExcelImporter
from timetable.interfaces.ui.client import ApiError, SolverApiClient


def main() -> None:
    st.title("Xếp thời khóa biểu")
    client = SolverApiClient()

    uploaded = st.file_uploader("Tải file Excel (sheet Phòng, Giáo viên, Lớp, Môn)", type=["xlsx"])
    if st.button("Giải", disabled=uploaded is None) and uploaded is not None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.xlsx"
            path.write_bytes(uploaded.getvalue())
            try:
                payload = OpenpyxlExcelImporter().load_data(path)
            except ExcelImportError as exc:
                st.error(str(exc))
                return
        try:
            job_id = client.submit(payload)
        except ApiError as exc:
            st.error(str(exc))
            return
        st.session_state["job_id"] = job_id

    current_job = st.session_state.get("job_id")
    if current_job:
        st.write(f"Job: `{current_job}`")
        placeholder = st.empty()
        try:
            for _ in range(120):
                info = client.job_status(current_job)
                placeholder.info(f"Trạng thái: {info['status']}")
                if client.is_final(info["status"]):
                    break
                time.sleep(2)
        except ApiError as exc:
            st.error(str(exc))


main()

import os
import sys
import streamlit as st
from datetime import timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import from src modules
from src.config.config import (
    APP_LAYOUT,
    SIDEBAR_STATE,
    DEFAULT_TIMEZONE,
)
from src.services.worklog_service import WorklogReport
from src.components.layout import AppLayout, DateSelector, TeamFilter
from src.components.visualization import DataVisualizer
from src.data.processors import DataProcessor

# Thiết lập trang
st.set_page_config(
    page_title="Worklog Report",
    page_icon="📊",
    layout=APP_LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE,
)

# Hiển thị tiêu đề
st.title("Worklog Report")

# Khởi tạo session_state nếu chưa có
if "report_data" not in st.session_state:
    st.session_state.report_data = None
if "date_range" not in st.session_state:
    st.session_state.date_range = None

# Date selection
start_date, end_date = DateSelector.display()

# Chuyển đổi date thành chuỗi ngày tháng
start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

# Kiểm tra xem date range có thay đổi không
current_date_range = (start_date_str, end_date_str)

# Chỉ gọi API nếu date range thay đổi hoặc chưa có dữ liệu
if (
    st.session_state.date_range != current_date_range
    or st.session_state.report_data is None
):
    # Hiển thị thông báo đang tải dữ liệu
    with st.spinner("Đang tải dữ liệu worklog..."):
        # Get worklog data using existing method
        worklog_report = WorklogReport()
        report_data = worklog_report.get_project_worklogs(start_date_str, end_date_str)

        # Lưu dữ liệu và date range vào session_state
        st.session_state.report_data = report_data
        st.session_state.date_range = current_date_range
else:
    # Sử dụng dữ liệu đã có từ session_state
    report_data = st.session_state.report_data

# Kiểm tra dữ liệu
if not report_data:
    st.error("No worklog data available for the selected period.")
else:
    # Hiển thị visualization
    DataVisualizer.display_visualizations(report_data)

# Show footer
st.markdown("---")
st.caption("© 2023 Jira Work Log Report")

# Hiển thị thông tin phiên bản
st.sidebar.markdown("---")
st.sidebar.caption("Jira Analytics v1.0.0")
st.sidebar.caption("© 2023 Jira Analytics")

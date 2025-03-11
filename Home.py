import streamlit as st
import os
import sys

# Thiết lập trang
st.set_page_config(
    page_title="Jira Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Tiêu đề trang chủ
st.title("Jira Analytics")

# Giới thiệu
st.markdown(
    """
## Chào mừng đến với Jira Analytics!

Ứng dụng này cung cấp các báo cáo và phân tích dữ liệu từ Jira, giúp bạn theo dõi tiến độ dự án và hiệu suất làm việc của đội ngũ.

### Các tính năng:

- **Worklog Report**: Báo cáo chi tiết về thời gian làm việc của các thành viên trong dự án
- **Issue Analytics**: *(Coming soon)* Phân tích dữ liệu các issue và nhiệm vụ 
- **Sprint Performance**: *(Coming soon)* Theo dõi hiệu suất sprint của đội ngũ

### Bắt đầu sử dụng:

Chọn trang "Worklog Report" từ sidebar bên trái để xem báo cáo thời gian làm việc.
"""
)

# Hiển thị thông tin phiên bản
st.sidebar.markdown("---")
st.sidebar.caption("Jira Analytics v1.0.0")
st.sidebar.caption("© 2023 Jira Analytics")

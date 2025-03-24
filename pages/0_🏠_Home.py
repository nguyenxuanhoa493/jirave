import streamlit as st

# Set page configuration first
st.set_page_config(
    page_title="Trang chủ | Jira Analytics",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="auto",
)

# Import thư viện tùy chỉnh
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.app_logo import add_logo

# Ẩn tất cả các menu mặc định
hide_default_format = """
<style>
#MainMenu {visibility: hidden;}
span[data-testid="stSidebarNavLinkText"] {visibility: hidden;}
</style>
"""
st.markdown(hide_default_format, unsafe_allow_html=True)

# Tùy chỉnh menu trong sidebar
with st.sidebar:
    st.markdown("## Jira Analytics")
    st.markdown("---")

    # Tạo các menu tùy chỉnh
    menu_items = [
        {"icon": "🏠", "name": "Trang chủ", "path": "Home"},
        {"icon": "🔍", "name": "Worklog", "path": "Issue_Detail"},
        {"icon": "🧩", "name": "Trường Tùy Chỉnh", "path": "Custom_Fields"},
        {"icon": "📊", "name": "Báo Cáo Sprint", "path": "Sprint_Report"},
        {"icon": "⏱️", "name": "Steve Estimate", "path": "Steve_Est"},
        {"icon": "🔄", "name": "Đồng bộ dữ liệu", "path": "Sync_Data"},
        {"icon": "📈", "name": "Kế hoạch Sprint", "path": "Sprint_Plan"},
    ]

    # Hiển thị các menu
    for item in menu_items:
        if st.button(
            f"{item['icon']} {item['name']}", key=item["path"], use_container_width=True
        ):
            # Do nothing here, the button will act as a link
            pass

    add_vertical_space(2)
    st.markdown("---")
    st.markdown("### Liên hệ")
    st.markdown("contact@jiraanalytics.com")

# Nội dung trang chủ
st.title("🏠 Jira Analytics")
st.markdown("## Chào mừng bạn đến với ứng dụng Jira Analytics")

st.markdown(
    """
Ứng dụng này cung cấp các công cụ phân tích và báo cáo cho Jira:

- **🔍 Worklog**: Xem chi tiết worklog của các issue
- **🧩 Trường Tùy Chỉnh**: Danh sách các trường tùy chỉnh trong Jira
- **📊 Báo Cáo Sprint**: Xem báo cáo tổng quan của sprint
- **⏱️ Steve Estimate**: Phân tích dữ liệu Steve Estimate
- **🔄 Đồng bộ dữ liệu**: Đồng bộ dữ liệu từ Jira
- **📈 Kế hoạch Sprint**: Lập kế hoạch cho sprint mới

Vui lòng chọn một tùy chọn từ thanh sidebar để bắt đầu.
"""
)

# Hiển thị thông tin phiên bản
st.sidebar.markdown("---")
st.sidebar.caption("Phiên bản: 1.0")

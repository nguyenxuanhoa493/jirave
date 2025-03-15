import os
import sys
import json
from datetime import datetime

# Thêm đường dẫn gốc vào Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import streamlit as st
from src.services.jira_client import JiraClient
from src.services.jira.base_client import BaseJiraClient
from src.config.config import DEFAULT_TIMEZONE
from src.utils.date_utils import get_current_time
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()


# Hàm che dữ liệu nhạy cảm
def mask_string(s, show_first=4, show_last=0):
    if not s:
        return "Không được cấu hình"
    if len(s) <= (show_first + show_last):
        return "*" * len(s)
    return (
        s[:show_first] + "*" * (len(s) - show_first - show_last) + s[-show_last:]
        if show_last > 0
        else s[:show_first] + "*" * (len(s) - show_first)
    )


# Thiết lập trang
st.set_page_config(
    page_title="Kiểm tra kết nối Jira",
    page_icon="🔌",
    layout="wide",
)

st.title("Kiểm tra kết nối đến Jira API")

# Hiển thị thông tin cấu hình
st.subheader("Thông tin cấu hình")
col1, col2, col3 = st.columns(3)

with col1:
    jira_url = os.environ.get("JIRA_URL", "")
    st.write("JIRA_URL:", jira_url or "Không được cấu hình")

with col2:
    email = os.environ.get("EMAIL", "")
    st.write("EMAIL:", email or "Không được cấu hình")

with col3:
    api_token = os.environ.get("API_TOKEN", "")
    st.write(
        "API_TOKEN:", mask_string(api_token) if api_token else "Không được cấu hình"
    )

st.divider()

# Thực hiện kiểm tra kết nối
st.subheader("Kiểm tra kết nối cơ bản")
with st.status("Đang thực hiện kiểm tra...", expanded=True) as status:
    # Tạo Jira client
    st.write("🔄 Khởi tạo Jira client...")
    try:
        jira_client = JiraClient()
        st.write("✅ Khởi tạo Jira client thành công")
    except Exception as e:
        st.error(f"❌ Lỗi khi khởi tạo Jira client: {str(e)}")
        st.stop()

    # Thử kết nối đến API
    st.write("🔄 Kiểm tra kết nối API...")
    try:
        # Test 1: Kiểm tra thông tin người dùng (myself)
        response = jira_client.get("myself")
        if response and response.status_code == 200:
            user_info = response.json()
            st.write("✅ Kết nối API thành công")
            st.write(
                f"👤 Đăng nhập với người dùng: {user_info.get('displayName')} ({user_info.get('emailAddress')})"
            )
        else:
            st.error(
                f"❌ Lỗi kết nối API: {response.status_code if response else 'Không có phản hồi'}"
            )
            if response:
                st.json(response.json())
    except Exception as e:
        st.error(f"❌ Lỗi khi kiểm tra kết nối: {str(e)}")

    # Kiểm tra quyền truy cập vào dự án
    st.write("🔄 Kiểm tra quyền truy cập vào dự án...")
    try:
        projects = jira_client.get_all_projects()
        if projects:
            st.write(f"✅ Có quyền truy cập vào {len(projects)} dự án")
            project_list = [f"{p.get('key')} - {p.get('name')}" for p in projects[:5]]
            st.write(
                "Ví dụ:", ", ".join(project_list) + ("..." if len(projects) > 5 else "")
            )
        else:
            st.warning("⚠️ Không tìm thấy dự án nào hoặc không có quyền truy cập")
    except Exception as e:
        st.error(f"❌ Lỗi khi lấy danh sách dự án: {str(e)}")

    # Kiểm tra trường tùy chỉnh
    st.write("🔄 Kiểm tra trường tùy chỉnh...")
    try:
        custom_fields = jira_client.get_custom_fields()
        if custom_fields:
            st.write(f"✅ Tìm thấy {len(custom_fields)} trường tùy chỉnh")
            cf_list = [
                f"{cf.get('name')} (ID: {cf.get('id')})" for cf in custom_fields[:3]
            ]
            st.write(
                "Ví dụ:", ", ".join(cf_list) + ("..." if len(custom_fields) > 3 else "")
            )
        else:
            st.warning("⚠️ Không tìm thấy trường tùy chỉnh nào")
    except Exception as e:
        st.error(f"❌ Lỗi khi lấy danh sách trường tùy chỉnh: {str(e)}")

    # Kiểm tra truy vấn JQL
    st.write("🔄 Kiểm tra truy vấn JQL cơ bản...")
    try:
        # Tạo truy vấn JQL đơn giản với ngày hiện tại
        today = get_current_time(DEFAULT_TIMEZONE).date().strftime("%Y-%m-%d")
        jql = f'created >= "{today}"'

        issues = jira_client.search_issues(jql=jql, max_results=5)
        if issues:
            st.write(f"✅ Truy vấn JQL thành công, tìm thấy {len(issues)} issue")
        else:
            st.write("✅ Truy vấn JQL thành công, không tìm thấy issue nào cho hôm nay")
    except Exception as e:
        st.error(f"❌ Lỗi khi thực hiện truy vấn JQL: {str(e)}")

    status.update(label="Kiểm tra hoàn tất", state="complete")

# Hiển thị bảng tổng hợp kết quả
st.subheader("Kết quả kiểm tra")
col1, col2 = st.columns(2)

with col1:
    st.info(
        "Để kiểm tra nâng cao hơn, bạn có thể vào trang 'Custom Fields' để xem chi tiết về các trường hoặc sử dụng công cụ Worklog Report để xem dữ liệu worklog."
    )

with col2:
    if "API_TOKEN" not in os.environ or not os.environ.get("API_TOKEN"):
        st.warning(
            "⚠️ API_TOKEN không được cấu hình trong biến môi trường. Hãy kiểm tra lại file .env"
        )
    if "EMAIL" not in os.environ or not os.environ.get("EMAIL"):
        st.warning(
            "⚠️ EMAIL không được cấu hình trong biến môi trường. Hãy kiểm tra lại file .env"
        )
    if "JIRA_URL" not in os.environ or not os.environ.get("JIRA_URL"):
        st.warning(
            "⚠️ JIRA_URL không được cấu hình trong biến môi trường. Hãy kiểm tra lại file .env"
        )

# Hiển thị thời gian kiểm tra
st.caption(f"Thời gian kiểm tra: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

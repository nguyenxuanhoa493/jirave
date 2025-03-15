import streamlit as st
import os
import sys
import json
import pandas as pd
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import from src modules
from src.config.config import (
    APP_TITLE,
    APP_LAYOUT,
    SIDEBAR_STATE,
    DEFAULT_TIMEZONE,
    DEFAULT_PROJECT,
)
from src.services.jira_client import JiraClient

# Set page configuration
st.set_page_config(
    page_title="Issue Detail", layout=APP_LAYOUT, initial_sidebar_state=SIDEBAR_STATE
)


class IssueDetailService:
    """Service for retrieving and displaying issue details"""

    def __init__(self):
        """Initialize the issue detail service"""
        self.jira = JiraClient()

    def get_issue_detail(self, issue_key):
        """Get detailed information for a specific issue

        Args:
            issue_key (str): The issue key (e.g., 'CLD-123')

        Returns:
            dict: The issue data if successful, None otherwise
        """
        try:
            # Lấy tất cả các trường cần thiết
            fields = "summary,status,issuetype,priority,assignee,reporter,created,updated,description,customfield_10016,timeoriginalestimate,timeestimate,timespent,customfield_10031"

            params = {"fields": fields}

            response = self.jira.get(f"issue/{issue_key}", params=params)
            if not response or response.status_code != 200:
                st.error(f"Không tìm thấy issue với key: {issue_key}")
                return None

            issue = response.json()

            # Lấy thêm worklog
            worklogs = self.jira.get_issue_worklogs(issue_key)
            issue["worklogs"] = worklogs

            return issue
        except Exception as e:
            st.error(f"Lỗi khi truy vấn issue: {str(e)}")
            return None

    def extract_basic_info(self, issue_data):
        """Extract basic information from issue data

        Args:
            issue_data (dict): The raw issue data

        Returns:
            dict: Basic information extracted from issue data
        """
        if not issue_data:
            return {}

        fields = issue_data.get("fields", {})

        # Xử lý assignee có thể None
        assignee_obj = fields.get("assignee") or {}
        assignee = assignee_obj.get("displayName", "Chưa gán")

        # Xử lý reporter có thể None
        reporter_obj = fields.get("reporter") or {}
        reporter = reporter_obj.get("displayName", "Không có")

        # Xử lý trường Tester (customfield_10031)
        tester = "Không có"
        cf_tester = fields.get("customfield_10031")
        if cf_tester:
            if isinstance(cf_tester, dict) and "displayName" in cf_tester:
                # Trường hợp tester là một user Jira
                tester = cf_tester.get("displayName", "Không có")
            elif isinstance(cf_tester, dict) and "value" in cf_tester:
                # Trường hợp tester là một trường tùy chỉnh với giá trị
                tester = cf_tester.get("value", "Không có")
            elif isinstance(cf_tester, list) and len(cf_tester) > 0:
                # Trường hợp tester là một danh sách (User Picker multiple users)
                # Chỉ lấy người dùng đầu tiên trong danh sách
                first_tester = cf_tester[0]
                if isinstance(first_tester, dict) and "displayName" in first_tester:
                    tester = first_tester.get("displayName", "Không có")
                elif isinstance(first_tester, dict) and "value" in first_tester:
                    tester = first_tester.get("value", "Không có")
                else:
                    tester = str(first_tester)
            else:
                # Trường hợp khác
                tester = str(cf_tester)

        # Xử lý các trường ngày tháng
        created = fields.get("created", "")
        updated = fields.get("updated", "")
        if created:
            created = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        if updated:
            updated = datetime.fromisoformat(updated.replace("Z", "+00:00")).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        # Trích xuất story points (thường trong customfield_10016)
        story_points = fields.get("customfield_10016")

        # Trích xuất time estimate (nếu có)
        original_estimate_seconds = fields.get("timeoriginalestimate")
        time_estimate_hours = (
            original_estimate_seconds / 3600 if original_estimate_seconds else None
        )

        # Trích xuất time spent (nếu có)
        time_spent_seconds = fields.get("timespent")
        time_spent_hours = time_spent_seconds / 3600 if time_spent_seconds else None

        return {
            "key": issue_data.get("key", ""),
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", ""),
            "issue_type": fields.get("issuetype", {}).get("name", ""),
            "priority": fields.get("priority", {}).get("name", ""),
            "assignee": assignee,
            "reporter": reporter,
            "tester": tester,
            "created": created,
            "updated": updated,
            "story_points": story_points,
            "time_estimate_hours": time_estimate_hours,
            "time_spent_hours": time_spent_hours,
            "description": fields.get("description", ""),
        }


def display_issue_search():
    """Display issue search form"""
    st.header("🔍 Tìm kiếm Issue")

    # Input form
    with st.form("issue_search_form"):
        issue_key = st.text_input("Nhập Issue Key (ví dụ: CLD-123)").strip().upper()
        submitted = st.form_submit_button("Tìm kiếm")

    # Trả về issue key nếu form được submit
    if submitted and issue_key:
        return issue_key

    return None


def display_basic_info(basic_info):
    """Display basic issue information in a structured format

    Args:
        basic_info (dict): Basic issue information
    """
    if not basic_info:
        return

    st.header(f"🔖 {basic_info['key']}: {basic_info['summary']}")

    # Hiển thị các thông tin cơ bản
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**Loại Issue:** {basic_info['issue_type']}")
    with col2:
        st.info(f"**Trạng thái:** {basic_info['status']}")
    with col3:
        st.info(f"**Độ ưu tiên:** {basic_info['priority']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**Người được gán:** {basic_info['assignee']}")
    with col2:
        st.info(f"**Người tạo:** {basic_info['reporter']}")
    with col3:
        st.info(f"**Người test:** {basic_info['tester']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        if basic_info["story_points"] is not None:
            st.metric("Story Points", basic_info["story_points"])
    with col2:
        if basic_info["time_estimate_hours"] is not None:
            st.metric("Thời gian ước tính", f"{basic_info['time_estimate_hours']:.2f}h")
    with col3:
        if basic_info["time_spent_hours"] is not None:
            st.metric("Thời gian đã dùng", f"{basic_info['time_spent_hours']:.2f}h")

    # Hiển thị thời gian tạo và cập nhật
    st.caption(
        f"**Tạo lúc:** {basic_info['created']} | **Cập nhật lúc:** {basic_info['updated']}"
    )

    # Hiển thị mô tả nếu có
    if basic_info["description"]:
        st.subheader("Mô tả")
        st.markdown(basic_info["description"])


def display_json_data(issue_data):
    """Display issue data in JSON format

    Args:
        issue_data (dict): The raw issue data
    """
    if not issue_data:
        return

    st.header("📄 Dữ liệu JSON")

    # Convert to JSON with indentation for readability
    json_str = json.dumps(issue_data, indent=2, ensure_ascii=False)

    # Display with code formatting
    st.code(json_str, language="json")

    # Add download button
    st.download_button(
        label="Tải xuống dữ liệu JSON",
        data=json_str,
        file_name=f"{issue_data.get('key', 'issue')}.json",
        mime="application/json",
    )


def display_worklog_table(issue_data):
    """Display issue worklog in table format

    Args:
        issue_data (dict): The raw issue data
    """
    if not issue_data or "worklogs" not in issue_data:
        return

    worklogs = issue_data["worklogs"]
    if not worklogs:
        st.info("Không có worklog nào cho issue này.")
        return

    st.header("⏱️ Worklog")

    # Process worklog data
    worklog_data = []
    for worklog in worklogs:
        # Extract author
        author = worklog.get("author", {}).get("displayName", "Unknown")

        # Format start time
        started = worklog.get("started", "")
        if started:
            started = datetime.fromisoformat(started.replace("Z", "+00:00")).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        # Calculate hours
        time_spent_seconds = worklog.get("timeSpentSeconds", 0)
        hours = time_spent_seconds / 3600

        # Extract comment
        comment = worklog.get("comment", "")

        worklog_data.append(
            {
                "Người dùng": author,
                "Thời gian": started,
                "Số giờ": f"{hours:.2f}h",
                "Ghi chú": comment,
            }
        )

    # Display table
    if worklog_data:
        df = pd.DataFrame(worklog_data)
        st.dataframe(df, use_container_width=True)

        # Calculate total hours
        total_hours = sum(
            worklog.get("timeSpentSeconds", 0) / 3600 for worklog in worklogs
        )
        st.metric("Tổng số giờ đã log", f"{total_hours:.2f}h")


def main():
    st.title("Chi tiết Issue")

    # Initialize service
    issue_service = IssueDetailService()

    # Display search form
    issue_key = display_issue_search()

    # If issue key provided, get and display issue details
    if issue_key:
        with st.spinner(f"Đang tìm kiếm issue {issue_key}..."):
            issue_data = issue_service.get_issue_detail(issue_key)

        if issue_data:
            # Extract and display basic info
            basic_info = issue_service.extract_basic_info(issue_data)
            display_basic_info(basic_info)

            # Display worklog table
            display_worklog_table(issue_data)

            # Display full JSON data
            with st.expander("Xem dữ liệu JSON đầy đủ"):
                display_json_data(issue_data)
    else:
        st.info("Nhập Issue Key và nhấn 'Tìm kiếm' để xem chi tiết issue.")


if __name__ == "__main__":
    main()

import streamlit as st
from datetime import datetime
from src.services.mongodb_client import is_running_in_streamlit
from src.config.config import DEFAULT_PROJECT


def sync_all_sprints(jira_client, show_toast=True, project_key=DEFAULT_PROJECT):
    """Đồng bộ tất cả các sprints của dự án

    Args:
        jira_client: Client kết nối đến Jira
        show_toast (bool): Hiển thị thông báo hay không
        project_key (str): Mã dự án

    Returns:
        list: Danh sách các sprints đã đồng bộ
    """
    if show_toast and is_running_in_streamlit():
        st.toast(f"Đang đồng bộ tất cả sprints của dự án {project_key}", icon="ℹ️")

    sprints = jira_client.get_all_sprints(project_key)

    if show_toast and is_running_in_streamlit():
        st.toast(
            f"Đã đồng bộ {len(sprints)} sprints của dự án {project_key}", icon="✅"
        )

    return sprints


def get_sprint_info(jira_client, sprint_id):
    """Lấy thông tin sprint từ API Jira

    Args:
        jira_client: Client kết nối đến Jira
        sprint_id (int): ID của sprint

    Returns:
        dict: Thông tin của sprint
    """
    try:
        # Lấy thông tin sprint từ API Jira
        sprint_info = jira_client.sprint_client.get(
            f"sprint/{sprint_id}", use_agile_api=True
        ).json()
        return sprint_info
    except Exception as e:
        if is_running_in_streamlit():
            st.error(f"Lỗi khi lấy thông tin sprint {sprint_id}: {str(e)}")
        return None


def get_sprint_date_range(sprint_info):
    """Lấy khoảng thời gian của sprint

    Args:
        sprint_info (dict): Thông tin sprint

    Returns:
        tuple: (sprint_start, sprint_end)
    """
    sprint_start = None
    sprint_end = None

    if sprint_info.get("startDate"):
        sprint_start = datetime.fromisoformat(
            sprint_info.get("startDate", "").replace("Z", "+00:00")
        )
    if sprint_info.get("endDate"):
        sprint_end = datetime.fromisoformat(
            sprint_info.get("endDate", "").replace("Z", "+00:00")
        )

    return sprint_start, sprint_end

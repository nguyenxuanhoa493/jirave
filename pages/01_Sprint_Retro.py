import streamlit as st
import os
import sys
from datetime import datetime, timedelta
from pages.sprint_display import display_sprint_overview

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
    page_title="Sprint Dashboard",
    layout=APP_LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE,
)


def main():
    st.title("Sprint Dashboard")

    # Initialize services
    jira_client = JiraClient()

    # Get all sprints for the project
    all_sprints = jira_client.get_all_sprints(DEFAULT_PROJECT)

    # Create a select box for sprint selection
    sprint_options = [sprint["name"] for sprint in all_sprints]

    # Tìm index của "CLD Sprint 10" nếu có trong danh sách
    default_index = 0
    if "CLD Sprint 10" in sprint_options:
        default_index = sprint_options.index("CLD Sprint 10")

    selected_sprint_name = st.selectbox(
        "Chọn sprint:", sprint_options, index=default_index
    )

    # Find the selected sprint
    selected_sprint = next(
        (sprint for sprint in all_sprints if sprint["name"] == selected_sprint_name),
        None,
    )

    # Get issues for the selected sprint
    issues = []
    if selected_sprint:
        issues = jira_client.get_sprint_issues(selected_sprint["id"])

    # Hiển thị tổng quan sprint
    if selected_sprint:
        display_sprint_overview(selected_sprint, issues)
    else:
        st.error("Không tìm thấy sprint đã chọn.")


if __name__ == "__main__":
    main()

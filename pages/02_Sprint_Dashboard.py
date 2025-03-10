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

    # Get active sprint
    active_sprint = jira_client.get_active_sprint(DEFAULT_PROJECT)

    # Lấy danh sách issue trong sprint
    issues = []
    if active_sprint:
        issues = jira_client.get_sprint_issues(active_sprint["id"])
        # st.dataframe(issues)

    # Hiển thị tổng quan sprint
    if active_sprint:
        display_sprint_overview(active_sprint, issues)
    else:
        st.error("Không tìm thấy sprint hiện tại.")


if __name__ == "__main__":
    main()

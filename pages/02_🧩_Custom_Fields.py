import streamlit as st

# Set page configuration first
st.set_page_config(
    page_title="Trường Tùy Chỉnh | Jira Analytics",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="auto",
)

import os
import sys
import json
import pandas as pd

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

# Function to display custom fields


def display_custom_fields():
    st.title("Thông tin các trường thông tin tuỳ chỉnh")
    jira_client = JiraClient()
    custom_fields = jira_client.get_custom_fields()
    if custom_fields:
        st.json(custom_fields)
    else:
        st.write("Không có trường tuỳ chỉnh nào được tìm thấy.")


def main():
    display_custom_fields()


if __name__ == "__main__":
    main()

import os
from dotenv import load_dotenv
import pytz
import streamlit as st

# Load environment variables
load_dotenv()

# Debug Mode
DEBUG = os.getenv("DEBUG") == "TRUE"

# API Configuration
API_TOKEN = os.getenv("JIRA_API_TOKEN")
EMAIL = os.getenv("JIRA_USER")
JIRA_URL = os.getenv("JIRA_URL")

# Default timezone
DEFAULT_TIMEZONE = "Asia/Bangkok"

# Project configuration
DEFAULT_PROJECT = "CLD"  # Default project key

# Application settings
APP_TITLE = "Tiến độ Sprint"
APP_LAYOUT = "wide"
SIDEBAR_STATE = "expanded"

# Date formats
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Chart colors
CHART_COLORS = {
    "primary": "rgba(0,128,255,0.7)",
    "secondary": "rgba(255,99,71,0.7)",
    "success": "rgba(0,255,0,0.6)",
    "warning": "rgba(255,255,0,0.6)",
    "danger": "rgba(255,0,0,0.6)",
}

# Heatmap color scale
HEATMAP_COLORSCALE = [
    [0, "rgba(255,0,0,0.6)"],
    [0.5, "rgba(255,255,0,0.6)"],
    [1, "rgba(0,255,0,0.6)"],
]

# Đường dẫn tới thư mục dữ liệu
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)
SPRINTS_DIR = os.path.join(DATA_DIR, "sprints")
ISSUES_DIR = os.path.join(DATA_DIR, "issues")
WORKLOGS_DIR = os.path.join(DATA_DIR, "worklogs")
CHANGELOG_DIR = os.path.join(DATA_DIR, "changelogs")

# Cache timeout (seconds)
CACHE_TTL = 3600  # 1 hour

# MongoDB settings
MONGO_HOST = os.environ.get("MONGO_HOST", "localhost")
MONGO_PORT = int(os.environ.get("MONGO_PORT", 27017))
MONGO_DB = os.environ.get("MONGO_DB", "jira_data")
MONGO_USER = os.environ.get("MONGO_USER", "")
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD", "")

# Jira API settings
JIRA_SERVER = os.environ.get("JIRA_SERVER", "https://jira.example.com")
JIRA_USERNAME = os.environ.get("JIRA_USERNAME", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")

# Các trường dữ liệu mặc định cần lấy từ Jira API
DEFAULT_FIELDS = [
    "summary",
    "status",
    "assignee",
    "issuetype",
    "customfield_10016",  # Story Points
    "created",
    "updated",
    "duedate",
    "fixVersions",
    "components",
    "labels",
    "description",
    "parent",
    "subtasks",
    "customfield_10032",  # Sprint
]

# Redis settings
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")

# Số lượng issues tối đa để hiển thị trong biểu đồ
MAX_ISSUES_IN_CHART = 50

# Thiết lập số lượng worker threads
NUM_WORKERS = 5

# Danh sách các trạng thái cuối cùng (done)
FINAL_STATUS_LIST = [
    "Done",
    "Closed",
    "Resolved",
    "UAT",
    "Dev Done",
    "QA Done",
]


# Thiết lập session state mặc định
def initialize_session_state():
    """Khởi tạo session state mặc định"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "jira_client" not in st.session_state:
        st.session_state.jira_client = None

    if "mongo_client" not in st.session_state:
        st.session_state.mongo_client = None


def get_timezone():
    """Returns the configured timezone object"""
    return pytz.timezone(DEFAULT_TIMEZONE)


FIELDS_CUSTOM_FIELD = {
    "Show in Dashboard": "Show in Dashboard",
    "Sprint Dashboard": "Sprint Dashboard",
}

# CSS cho bảng hiển thị tailwind
TAILWIND_TABLE_CSS = """
<style>
.tailwind-table {
    margin-top: 10px;
    width: 100%;
    border-collapse: collapse;
    border-spacing: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    border-radius: 8px;
    overflow: hidden;
}

.tailwind-table th {
    background-color: #f3f4f6;
    font-weight: 600;
    text-align: center; /* Căn giữa header */
    padding: 12px 16px;
    border-bottom: 2px solid #e5e7eb;
    color: #374151;
    text-transform: uppercase;
    font-size: 14px;
    letter-spacing: 0.05em;
}

.tailwind-table td {
    padding: 12px 16px;
    border-bottom: 1px solid #e5e7eb;
    color: #1f2937;
    vertical-align: middle;
}

.tailwind-table tr:hover {
    background-color: #f9fafb;
    transition: background-color 0.2s ease;
}

.tailwind-table tr:last-child td {
    border-bottom: none;
}

.tailwind-table a {
    color: #2563eb;
    text-decoration: none;
    font-weight: 500;
}

.tailwind-table a:hover {
    text-decoration: underline;
    color: #1d4ed8;
}

/* Các màu sắc khác cho hàng chẵn/lẻ */
.tailwind-table tr:nth-child(odd) {
    background-color: #ffffff;
}

.tailwind-table tr:nth-child(even) {
    background-color: #f9fafb;
}
</style>
"""

# CSS cho group table với các nhóm hiển thị mặc định
GROUP_TABLE_CSS = """
<style>
.tailwind-table {
    margin-top: 10px;
    width: 100%;
    border-collapse: collapse;
    border-spacing: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    border-radius: 8px;
    overflow: hidden;
}

.tailwind-table th {
    background-color: #f3f4f6;
    font-weight: 600;
    text-align: center;
    padding: 12px 16px;
    border-bottom: 2px solid #e5e7eb;
    color: #374151;
    text-transform: uppercase;
    font-size: 14px;
    letter-spacing: 0.05em;
}

.tailwind-table td {
    padding: 12px 16px;
    border-bottom: 1px solid #e5e7eb;
    color: #1f2937;
    vertical-align: middle;
}

.group-header {
    background-color: #e5e7eb;
    font-weight: bold;
}

.group-header td {
    padding: 12px 16px !important; 
}

.group-header:hover {
    background-color: #d1d5db;
}

.group-row {
    background-color: #f9fafb;
}

.group-row:hover {
    background-color: #f3f4f6;
}

.inner-table {
    width: 100%;
    border-collapse: collapse;
}

.inner-table td {
    padding: 10px 16px;
    border-bottom: 1px solid #e5e7eb;
}

.tailwind-table a {
    color: #2563eb;
    text-decoration: none;
    font-weight: 500;
}

.tailwind-table a:hover {
    text-decoration: underline;
    color: #1d4ed8;
}
</style>
"""

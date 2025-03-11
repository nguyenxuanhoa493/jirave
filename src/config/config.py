import os
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# API Configuration
API_TOKEN = os.getenv("API_TOKEN")
EMAIL = os.getenv("EMAIL")
JIRA_URL = os.getenv("JIRA_URL")

# Default timezone
DEFAULT_TIMEZONE = "Asia/Bangkok"

# Project configuration
DEFAULT_PROJECT = "CLD"  # Default project key

# Application settings
APP_TITLE = "Worklog Report"
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

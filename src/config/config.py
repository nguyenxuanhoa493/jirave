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
APP_TITLE = "📊 Jira Worklog Report"
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

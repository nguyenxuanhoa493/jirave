import streamlit as st
from datetime import datetime, timedelta
from src.utils.date_utils import (
    get_current_time,
    get_week_start_end,
    get_last_week_start_end,
)
from src.config.config import DEFAULT_TIMEZONE


class DateSelector:
    """Class quản lý việc chọn khoảng thời gian trong ứng dụng"""

    @staticmethod
    def display():
        """Hiển thị giao diện chọn khoảng thời gian

        Returns:
            tuple: (start_date, end_date) được chọn
        """
        # Set default time to morning in timezone
        today = get_current_time(DEFAULT_TIMEZONE).replace(
            hour=9, minute=0, second=0, microsecond=0
        )

        # Date selection in columns
        col1, col2, col3 = st.columns(3)

        with col1:
            report_type = st.selectbox(
                "Select Report Period",
                [
                    "Today",
                    "Yesterday",
                    "This week",
                    "Last week",
                    "Last 7 days",
                    "Custom",
                ],
                index=0,  # Mặc định là Today
            )

        # Xử lý các loại báo cáo khác nhau
        if report_type == "Today":
            start_date = today.date()
            end_date = today.date()
        elif report_type == "Yesterday":
            start_date = (today - timedelta(days=1)).date()
            end_date = (today - timedelta(days=1)).date()
        elif report_type == "This week":
            start_date, end_date = get_week_start_end(today)
        elif report_type == "Last week":
            start_date, end_date = get_last_week_start_end()
        elif report_type == "Last 7 days":
            start_date = (today - timedelta(days=6)).date()
            end_date = today.date()
        else:  # Custom
            with col2:
                start_date = st.date_input("Start Date")
            with col3:
                end_date = st.date_input("End Date")

        return start_date, end_date


class TeamFilter:
    """Class quản lý việc lọc nhóm và người dùng"""

    @staticmethod
    def display(available_teams=None):
        """Hiển thị giao diện lọc team và user

        Args:
            available_teams (list, optional): Danh sách các team có sẵn

        Returns:
            tuple: (selected_team, filter_by_user, hide_inactive)
        """
        if available_teams is None:
            available_teams = []

        # Thêm tùy chọn "All Teams" nếu có nhiều team
        if len(available_teams) > 1:
            team_options = ["All Teams"] + available_teams
        else:
            team_options = available_teams

        # Team selection
        selected_team = st.selectbox("Select Team", team_options)

        # User filter options
        filter_cols = st.columns(2)

        with filter_cols[0]:
            filter_by_user = st.checkbox("Filter by user name", value=False)

        with filter_cols[1]:
            hide_inactive = st.checkbox("Hide inactive users (0 hours)", value=True)

        return selected_team, filter_by_user, hide_inactive


class AppLayout:
    """Class quản lý bố cục tổng thể của ứng dụng"""

    @staticmethod
    def setup_page(title, layout="wide", sidebar_state="expanded"):
        """Thiết lập cấu hình trang

        Args:
            title (str): Tiêu đề của trang
            layout (str, optional): Bố cục (wide/centered)
            sidebar_state (str, optional): Trạng thái sidebar
        """
        st.set_page_config(
            page_title=title, layout=layout, initial_sidebar_state=sidebar_state
        )

    @staticmethod
    def show_header(title):
        """Hiển thị tiêu đề và header của ứng dụng

        Args:
            title (str): Tiêu đề ứng dụng
        """
        st.title(title)

    @staticmethod
    def show_footer():
        """Hiển thị footer của ứng dụng"""
        st.markdown("---")
        st.caption("© 2023 Jira Work Log Report")

    @staticmethod
    def show_error(message):
        """Hiển thị thông báo lỗi

        Args:
            message (str): Thông báo lỗi
        """
        st.error(message)

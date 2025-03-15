import streamlit as st
from src.services.jira_client import JiraClient
from src.config.config import DEFAULT_PROJECT
from datetime import datetime, date
from src.utils.date_utils import get_current_time
from src.config.config import DEFAULT_TIMEZONE


class WorklogReport:
    """Service for generating worklog reports from Jira data"""

    def __init__(self, project_key=DEFAULT_PROJECT):
        """Initialize the worklog report service

        Args:
            project_key (str, optional): The Jira project key to report on
        """
        self.jira = JiraClient()
        self.project_key = project_key

    def get_project_worklogs(self, start_date=None, end_date=None, project_key=None):
        """Get worklogs for a project within a date range

        Args:
            start_date (str): Start date in format 'YYYY-MM-DD'
            end_date (str, optional): End date in format 'YYYY-MM-DD'
            project_key (str, optional): Project key to override the default

        Returns:
            dict: Processed worklog data organized by user, issue, and date
        """
        if project_key is None:
            project_key = self.project_key

        # Xác thực ngày để tránh truy vấn với ngày trong tương lai
        today = get_current_time(DEFAULT_TIMEZONE).date().strftime("%Y-%m-%d")

        # Chuyển đổi chuỗi ngày thành đối tượng datetime.date để so sánh
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            if end_date:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            else:
                end_date_obj = start_date_obj

            today_obj = datetime.strptime(today, "%Y-%m-%d").date()

            # Giới hạn ngày
            if start_date_obj > today_obj:
                start_date = today
                st.warning(
                    f"Ngày bắt đầu trong tương lai, đã điều chỉnh thành ngày hiện tại: {today}"
                )

            if end_date_obj > today_obj:
                end_date = today
                st.warning(
                    f"Ngày kết thúc trong tương lai, đã điều chỉnh thành ngày hiện tại: {today}"
                )
        except Exception as e:
            st.error(f"Lỗi khi xác thực ngày: {str(e)}")
            # Sử dụng ngày hôm nay nếu có lỗi
            start_date = today
            end_date = today

        # Build JQL query
        jql = f'project = {project_key} AND worklogDate >= "{start_date}"'
        if end_date:
            jql += f' AND worklogDate <= "{end_date}"'

        try:
            # Get issues with worklogs
            issues = self.jira.search_issues(
                jql=jql, fields=["worklog", "summary", "assignee"], max_results=1000
            )

            if not issues:
                st.warning(
                    f"No issues found with worklogs in the date range for project {project_key}"
                )
                return None

            return self._process_worklogs(issues, start_date, end_date)
        except Exception as e:
            st.error(f"Lỗi khi lấy dữ liệu từ API: {str(e)}")
            return None

    def _process_worklogs(self, issues, start_date, end_date):
        """Process raw worklog data into structured format

        Args:
            issues (list): List of issue data from Jira API
            start_date (str): Start date in format 'YYYY-MM-DD'
            end_date (str): End date in format 'YYYY-MM-DD'

        Returns:
            dict: Processed worklog data organized by user, issue, and date
        """
        worklog_data = {
            "by_user": {},  # Total hours by user
            "by_issue": {},  # Issue details with worklogs
            "daily_summary": {},  # Hours by date and user
            "total_hours": 0,  # Total hours across all users
        }

        # Process each issue
        for issue in issues:
            issue_id = issue["id"]
            issue_key = issue["key"]

            # Get detailed worklogs for this issue
            worklogs = self.jira.get_issue_worklogs(issue_key)

            if not worklogs:
                continue

            # Store issue summary for reference
            worklog_data["by_issue"][issue_key] = {
                "summary": issue["fields"]["summary"],
                "worklogs": [],
            }

            # Process each worklog entry
            for worklog in worklogs:
                worklog_date = worklog["started"][:10]  # Extract date part

                # Only include worklogs in the specified date range
                if start_date <= worklog_date <= end_date:
                    author = worklog["author"]["displayName"]
                    time_spent_hours = worklog["timeSpentSeconds"] / 3600

                    # Lấy avatar URL của tác giả nếu có
                    avatar_url = (
                        worklog["author"].get("avatarUrls", {}).get("24x24", "")
                    )

                    # Aggregate by user
                    if author not in worklog_data["by_user"]:
                        worklog_data["by_user"][author] = 0
                    worklog_data["by_user"][author] += time_spent_hours

                    # Store detailed worklog for this issue
                    worklog_data["by_issue"][issue_key]["worklogs"].append(
                        {
                            "author": author,
                            "avatar_url": avatar_url,
                            "date": worklog_date,
                            "hours": time_spent_hours,
                            "comment": worklog.get("comment", ""),
                        }
                    )

                    # Aggregate by date and user
                    if worklog_date not in worklog_data["daily_summary"]:
                        worklog_data["daily_summary"][worklog_date] = {}
                    if author not in worklog_data["daily_summary"][worklog_date]:
                        worklog_data["daily_summary"][worklog_date][author] = 0
                    worklog_data["daily_summary"][worklog_date][
                        author
                    ] += time_spent_hours

                    # Update total hours
                    worklog_data["total_hours"] += time_spent_hours

        return worklog_data

    def get_available_projects(self):
        """Get list of available projects

        Returns:
            list: List of project dictionaries with 'key' and 'name'
        """
        projects = self.jira.get_all_projects()
        return [{"key": p["key"], "name": p["name"]} for p in projects]

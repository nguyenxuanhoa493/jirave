import streamlit as st
from src.services.jira.issue_client import IssueClient
from src.services.jira.worklog_client import WorklogClient
from src.services.jira.project_client import ProjectClient
from src.services.jira.sprint_client import SprintClient
from src.services.jira.custom_field_client import CustomFieldClient


class JiraClientFacade:
    """Facade for all specialized Jira clients to maintain compatibility with existing code"""

    def __init__(self):
        """Initialize all specialized clients"""
        self.issue_client = IssueClient()
        self.worklog_client = WorklogClient()
        self.project_client = ProjectClient()
        self.sprint_client = SprintClient()
        self.custom_field_client = CustomFieldClient()

    # Base methods delegate
    def get(self, endpoint, params=None, use_agile_api=False):
        """Delegate to base client method"""
        return self.issue_client.get(endpoint, params, use_agile_api)

    def post(self, endpoint, payload):
        """Delegate to base client method"""
        return self.issue_client.post(endpoint, payload)

    def put(self, endpoint, payload):
        """Delegate to base client method"""
        return self.issue_client.put(endpoint, payload)

    def _make_request(self, endpoint):
        """Delegate to base client method"""
        return self.issue_client._make_request(endpoint)

    # Issue methods
    def get_issue(self, issue_key, custom_field_ids=None):
        """Delegate to issue client"""
        return self.issue_client.get_issue(issue_key, custom_field_ids)

    def search_issues(self, jql, fields=None, max_results=1000):
        """Delegate to issue client"""
        return self.issue_client.search_issues(jql, fields, max_results)

    def get_issue_types(self, project_key):
        """Delegate to issue client"""
        return self.issue_client.get_issue_types(project_key)

    def update_issue(self, issue_key, fields_data):
        """Delegate to issue client"""
        return self.issue_client.update_issue(issue_key, fields_data)

    # Worklog methods
    def get_issue_worklogs(self, issue_key):
        """Delegate to worklog client"""
        return self.worklog_client.get_issue_worklogs(issue_key)

    def add_worklog(self, issue_key, time_spent, start_time=None, comment=None):
        """Delegate to worklog client"""
        return self.worklog_client.add_worklog(
            issue_key, time_spent, start_time, comment
        )

    # Project methods
    def get_all_projects(self):
        """Delegate to project client"""
        return self.project_client.get_all_projects()

    def get_project_statuses(self, project_key):
        """Delegate to project client"""
        return self.project_client.get_project_statuses(project_key)

    def get_project_boards(self, project_key):
        """Delegate to project client"""
        return self.project_client.get_project_boards(project_key)

    # Sprint methods
    def get_board_sprints(self, board_id, state=None):
        """Delegate to sprint client"""
        return self.sprint_client.get_board_sprints(board_id, state)

    def get_sprint_issues(
        self, sprint_id, fields=None, status_names=None, max_issues=1000, project_key=None
    ):
        """Delegate to sprint client

        Args:
            sprint_id (int): ID của sprint
            fields (list, optional): Danh sách các trường cần lấy
            status_names (list, optional): Lọc theo tên trạng thái
            max_issues (int, optional): Số lượng issues tối đa cần lấy, mặc định 1000
                                        Nếu max_issues=-1, sẽ lấy tất cả issues
            project_key (str, optional): Mã dự án cần lọc

        Returns:
            list: Danh sách issues
        """
        return self.sprint_client.get_sprint_issues(
            sprint_id, fields, status_names, max_issues, project_key
        )

    def get_sprint_report(self, board_id, sprint_id):
        """Delegate to sprint client"""
        return self.sprint_client.get_sprint_report(board_id, sprint_id)

    def get_active_sprint(self, project_key):
        """Delegate to sprint client"""
        return self.sprint_client.get_active_sprint(project_key)

    def get_all_sprints(self, project_key):
        """Get all sprints for a project"""
        # Lấy tất cả các board của project
        boards = self.get_project_boards(project_key)
        all_sprints = []

        for board in boards:
            board_id = board["id"]
            sprints = self.get_board_sprints(board_id)
            all_sprints.extend(sprints)

        return all_sprints

    # Custom field methods
    def get_custom_fields(self):
        """Delegate to custom field client"""
        return self.custom_field_client.get_custom_fields()

    def get_field_details(self, field_id):
        """Delegate to custom field client"""
        return self.custom_field_client.get_field_details(field_id)

    def get_custom_field_id(self, field_name):
        """Delegate to custom field client"""
        return self.custom_field_client.get_custom_field_id(field_name)

    def update_custom_fields(self, issues, data_set):
        """Delegate to custom field client"""
        return self.custom_field_client.update_custom_fields(issues, data_set)
